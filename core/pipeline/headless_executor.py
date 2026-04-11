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
        self.realtime = realtime
        self.auto_loop = auto_loop
        self.callbacks = callbacks or {}
        
        self.running = False
        self.paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._seek_position = -1
        
        # Ресурсы
        self.detector = None
        self.data_logger = None
        self.monitor = ResourceMonitor()
        self.visualizer = Visualizer() if 'on_frame' in self.callbacks else None
        
        # Состояние и статистика
        self.frame_count = 0
        self.last_detections = []
        self.meta = {}
        self.unique_ids = {"staff": set(), "client": set()}
        self.start_time = 0
        self.total_time = 0

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
        self._pause_event.set()

    def prepare(self):
        """Подготовка ресурсов перед запуском цикла."""
        cap = cv2.VideoCapture(self.source_path)

        if not cap.isOpened():
            logger.error(f"Не удалось открыть источник: {self.source_path}")
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        filename = os.path.basename(self.source_path)
        nvr_meta = parse_nvr_filename(filename)
        camera_id = nvr_meta.get("camera_id", "unknown")

        self.meta = {
            "camera_id": camera_id,
            "filename": filename,
            "fps": float(fps) if fps > 0 else 25.0,
            "width": width,
            "height": height,
            "total_frames": total_frames
        }
        self.meta.update(nvr_meta)

        self.detector, _ = PipelineFactory.create_detector_tracker(self.source_path, camera_id_override=camera_id)
        self.detector.fps = self.meta["fps"]

        self.data_logger, _ = PipelineFactory.create_data_logger(self.source_path)
        self.data_logger.metadata = self.meta
        self.data_logger.open()
        
        self.detector.data_logger = self.data_logger

        if 'on_duration' in self.callbacks:
            self.callbacks['on_duration'](total_frames)
            
        if 'on_meta' in self.callbacks:
            self.callbacks['on_meta'](self.meta)
            
        return cap


    def run(self):
        """Запускает полный цикл обработки видео."""
        cap = self.prepare()

        if not cap:
            return False

        self.running = True
        self.start_time = time.time()
        
        cfg_perf = config.settings.system.perf
        cfg_analytics = config.settings.analytics
        is_stream = not (isinstance(self.source_path, str) and os.path.isfile(self.source_path))

        logger.info(f"Запуск обработки {self.meta['filename']} (Batch: {self.batch_size}, Realtime: {self.realtime})...")

        try:
            while self.running:
                iteration_start = time.perf_counter()

                if self._seek_position >= 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, self._seek_position)
                    self.frame_count = self._seek_position
                    self._seek_position = -1
                    if hasattr(self, '_batch_frames'):
                        self._batch_frames, self._batch_ids = [], []


                if self.paused:
                    if is_stream: 
                        cap.grab()
                    self._pause_event.wait(timeout=0.1)
                    continue

                is_processing_frame = self.frame_count % cfg_perf.frame_interval == 0
                if is_processing_frame:
                    ret, frame = cap.read()
                else:
                    ret, frame = cap.grab(), None
                    
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
                    self._handle_batch(frame, self.frame_count, cfg_analytics)
                
                if 'on_frame' in self.callbacks and frame is not None:
                    vis_frame = self.visualizer.draw(frame, self.last_detections, 
                                                   roi=cfg_analytics.roi, 
                                                   staff_auto_zones=cfg_analytics.staff_zones)
                    self.callbacks['on_frame'](vis_frame)

                if self.frame_count % 30 == 0 and 'on_performance' in self.callbacks:
                    self.callbacks['on_performance'](self.monitor.get_stats())

                if self.realtime and self.meta['fps'] > 0:
                    elapsed = time.perf_counter() - iteration_start
                    delay = max(0, (1 / self.meta['fps']) - elapsed)
                    if delay > 0: 
                        time.sleep(delay)

        finally:
            self.total_time = time.time() - self.start_time
            cap.release()
            if self.data_logger:
                self.data_logger.close()
            logger.info(f"Обработка завершена. Кадров: {self.frame_count}, Время: {self.total_time:.1f}s")
        
        return True

    def _handle_batch(self, frame, frame_id, cfg_analytics):
        """Внутренняя обработка батчинга."""
        if not hasattr(self, '_batch_frames'):
            self._batch_frames, self._batch_ids = [], []

        self._batch_frames.append(frame)
        self._batch_ids.append(frame_id)

        if len(self._batch_frames) >= self.batch_size:
            self.last_detections = self._process_and_emit(self._batch_frames, self._batch_ids, cfg_analytics)
            self._batch_frames, self._batch_ids = [], []

    def _process_and_emit(self, frames, ids, cfg_analytics):
        detections = []
        start_proc = time.perf_counter()
        
        if self.batch_size > 1:
            batch_results = self.detector.process_batch(frames, frame_ids=ids,
                                                      roi=cfg_analytics.roi,
                                                      staff_zones=cfg_analytics.staff_zones)
            if batch_results:
                # Учитываем статистику для всех кадров батча
                for d_list, _ in batch_results:
                    self._update_stats(d_list)
                detections, _ = batch_results[-1]
        else:
            detections, _ = self.detector.process_frame(frames[0], frame_id=ids[0],
                                                       roi=cfg_analytics.roi,
                                                       staff_zones=cfg_analytics.staff_zones)
            self._update_stats(detections)
        
        # Обновляем мониторинг прикладными метриками
        proc_ms = (time.perf_counter() - start_proc) * 1000
        self.monitor.update(inference_ms=proc_ms)

        if 'on_stats' in self.callbacks:
            self.callbacks['on_stats'](detections)
        return detections

    def _update_stats(self, detections):
        """Обновление счетчиков уникальных ID."""
        for d in detections:
            role = d.get('role', 'client')
            tid = d.get('track_id')
            if tid is not None:
                self.unique_ids[role].add(tid)

    def get_summary(self):
        """Возвращает итоговую статистику обработки."""
        return {
            'total_frames': self.meta.get('total_frames', 0),
            'processed_frames': self.frame_count,
            'staff_count': len(self.unique_ids['staff']),
            'client_count': len(self.unique_ids['client']),
            'total_time': self.total_time,
            'avg_fps': self.frame_count / self.total_time if self.total_time > 0 else 0,
            'filename': self.meta.get('filename', '')
        }


