import cv2
import os
import logging
import time
import threading
import config
from core.pipeline.factory import PipelineFactory
from utils.filename_parser import parse_nvr_filename
from core.analytics.monitor import ResourceMonitor
from utils.visualizer import Visualizer

logger = logging.getLogger(__name__)

class HeadlessExecutor:
    """
    Универсальный исполнитель для обработки видео.
    Централизованная логика для CLI и GUI (через VideoWorker).
    """
    def __init__(self, source_path, weights=None, device=None, batch_size=1, callbacks=None, realtime=False, auto_loop=True):
        self.source_path = source_path
        self.weights = weights or config.settings.yolo.weights
        self.device = device or config.settings.system.perf.device
        self.batch_size = batch_size
        self.realtime = realtime # Если True, соблюдает FPS видео
        self.auto_loop = auto_loop
        self.callbacks = callbacks or {} # on_frame, on_stats, on_progress, on_performance, on_duration

        
        self.running = False
        self.paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._seek_position = -1
        
        self.detector = None
        self.data_logger = None
        self.monitor = ResourceMonitor()
        self.visualizer = Visualizer() if 'on_frame' in self.callbacks else None
        
        self.last_detections = []
        self.frame_count = 0

    def set_paused(self, p):
        self.paused = p
        if p:
            self._pause_event.clear()
        else:
            self._pause_event.set()

    def set_position(self, pos):
        self._seek_position = pos

    def stop(self):
        self.running = False
        self._pause_event.set() # Разблокируем, если стояло на паузе

    def run(self):
        """Запускает полный цикл обработки видео."""
        self.running = True
        
        cfg_perf = config.settings.system.perf
        cfg_analytics = config.settings.analytics
        
        cap = cv2.VideoCapture(self.source_path)
        if not cap.isOpened():
            logger.error(f"Не удалось открыть источник: {self.source_path}")
            return False

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            filename = os.path.basename(self.source_path)
            nvr_meta = parse_nvr_filename(filename)
            camera_id = nvr_meta.get("camera_id", "unknown")

            meta = {
                "camera_id": camera_id,
                "filename": filename,
                "fps": float(fps) if fps > 0 else 25.0,
                "width": width,
                "height": height,
                "total_frames": total_frames
            }
            meta.update(nvr_meta)

            # Инициализация через фабрику
            self.detector, _ = PipelineFactory.create_detector_tracker(self.source_path, camera_id_override=camera_id)
            self.detector.fps = meta["fps"]

            self.data_logger, _ = PipelineFactory.create_data_logger(self.source_path)
            self.data_logger.metadata = meta
            self.data_logger.open()
            
            self.detector.data_logger = self.data_logger

            if 'on_duration' in self.callbacks:
                self.callbacks['on_duration'](total_frames)

            logger.info(f"Начало обработки {filename} (Batch: {self.batch_size}, Realtime: {self.realtime})...")

        except Exception as e:
            logger.error(f"Ошибка инициализации HeadlessExecutor: {e}")
            cap.release()
            return False

        self.frame_count = 0
        batch_frames = []
        batch_ids = []

        is_stream = not (isinstance(self.source_path, str) and os.path.isfile(self.source_path))

        try:
            while self.running:
                iteration_start = time.perf_counter()

                # Обработка перемотки
                if self._seek_position >= 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, self._seek_position)
                    self.frame_count = self._seek_position
                    self._seek_position = -1
                    batch_frames, batch_ids = [], []

                # Обработка паузы
                if self.paused:
                    if is_stream:
                        cap.grab() # Сбрасываем буфер для стримов
                    self._pause_event.wait(timeout=0.1)
                    continue


                is_processing_frame = self.frame_count % cfg_perf.frame_interval == 0
                
                if is_processing_frame:
                    ret, frame = cap.read()
                else:
                    ret = cap.grab()
                    frame = None
                    
                if not ret:
                    if not is_stream and self.auto_loop and self.running:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.frame_count = 0
                        continue
                    break

                    
                self.frame_count += 1
                self.monitor.update()
                
                if 'on_progress' in self.callbacks:
                    self.callbacks['on_progress'](self.frame_count)

                if is_processing_frame:
                    batch_frames.append(frame)
                    batch_ids.append(self.frame_count)

                    if len(batch_frames) >= self.batch_size:
                        self.last_detections = self._process_and_emit(batch_frames, batch_ids, cfg_analytics)
                        batch_frames, batch_ids = [], []
                
                # Визуализация (если нужен вывод кадра)
                if 'on_frame' in self.callbacks and frame is not None:
                    vis_frame = self.visualizer.draw(
                        frame,
                        self.last_detections,
                        roi=cfg_analytics.roi,
                        staff_auto_zones=cfg_analytics.staff_zones
                    )
                    self.callbacks['on_frame'](vis_frame)

                # Мониторинг ресурсов
                if self.frame_count % 30 == 0 and 'on_performance' in self.callbacks:
                    self.callbacks['on_performance'](self.monitor.get_stats())

                # Адаптивная задержка для Realtime
                if self.realtime and fps > 0:
                    elapsed = time.perf_counter() - iteration_start
                    delay = max(0, (1 / fps) - elapsed)
                    if delay > 0:
                        time.sleep(delay)

            # Дорабатываем остатки батча
            if batch_frames:
                self.last_detections = self._process_and_emit(batch_frames, batch_ids, cfg_analytics)

        finally:
            cap.release()
            if self.data_logger:
                self.data_logger.close()
            logger.info(f"Обработка {filename} завершена. Кадров: {self.frame_count}")
        
        return True

    def _process_and_emit(self, frames, ids, cfg_analytics):
        detections = []
        if self.batch_size > 1:
            batch_results = self.detector.process_batch(
                frames, 
                frame_ids=ids,
                roi=cfg_analytics.roi,
                staff_zones=cfg_analytics.staff_zones
            )
            if batch_results:
                detections, _ = batch_results[-1]
        else:
            detections, _ = self.detector.process_frame(
                frames[0], 
                frame_id=ids[0],
                roi=cfg_analytics.roi,
                staff_zones=cfg_analytics.staff_zones
            )
        
        if 'on_stats' in self.callbacks:
            self.callbacks['on_stats'](detections)
        
        return detections

