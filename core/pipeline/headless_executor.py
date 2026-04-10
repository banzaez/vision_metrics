import cv2
import os
import logging
import config
from core.pipeline.orchestrator import DetectorTracker
from core.analytics.data_logger import JSONDataLogger
from utils.filename_parser import extract_camera_id, parse_nvr_filename
from utils.monitor import ResourceMonitor

logger = logging.getLogger(__name__)

class HeadlessExecutor:
    """
    Универсальный исполнитель для обработки видео без GUI.
    Может использоваться как в CLI-скриптах, так и внутри VideoWorker.
    """
    def __init__(self, source_path, weights=None, device=None, batch_size=1, callbacks=None):
        self.source_path = source_path
        self.weights = weights or config.settings.yolo.weights
        self.device = device or config.settings.system.perf.device
        self.batch_size = batch_size
        self.callbacks = callbacks or {} # Словарь функций: on_frame, on_stats, on_progress
        
        self.running = False
        self.detector = None
        self.data_logger = None
        self.monitor = ResourceMonitor()

    def run(self):
        """Запускает полный цикл обработки видео с поддержкой батчей."""
        self.running = True
        
        # 1. Загрузка компонентов
        try:
            cfg_perf = config.settings.system.perf
            cfg_analytics = config.settings.analytics
            
            filename = os.path.basename(self.source_path)
            nvr_meta = parse_nvr_filename(filename)
            extracted_camera_id = nvr_meta.get("camera_id", "unknown")

            self.detector = DetectorTracker(
                model_path=self.weights,
                camera_id=extracted_camera_id,
                device=self.device,
                half=cfg_perf.half
            )
            
            # Инициализация и настройка логгера (вся логика путей теперь внутри!)
            self.data_logger = JSONDataLogger()
            self.data_logger.setup_from_video(self.source_path)
            
        except Exception as e:
            logger.error(f"Ошибка инициализации HeadlessExecutor: {e}")
            return False

        # 2. Видео захват
        cap = cv2.VideoCapture(self.source_path)
        if not cap.isOpened():
            logger.error(f"Не удалось открыть источник: {self.source_path}")
            return False

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Передаем метаданные логгеру
        meta = {
            "camera_id": self.detector.camera_id,
            "filename": filename,
            "fps": float(fps) if fps > 0 else 25.0,
            "width": width,
            "height": height,
            "total_frames": total_frames
        }
        self.data_logger.metadata = meta
        # Добавляем расширенные данные из имени файла
        self.data_logger.metadata.update(nvr_meta)
        self.data_logger.open()
        
        # Настраиваем оркестратор (унифицированная логика)
        self.detector.fps = meta["fps"]
        self.detector.data_logger = self.data_logger
        
        if 'on_duration' in self.callbacks:
            self.callbacks['on_duration'](total_frames)

        frame_count = 0
        logger.info(f"Начало обработки {filename} (Batch Size: {self.batch_size})...")

        batch_frames = []
        batch_ids = []

        try:
            while self.running:
                is_processing_frame = frame_count % cfg_perf.frame_interval == 0
                
                if is_processing_frame:
                    ret, frame = cap.read()
                else:
                    ret = cap.grab()
                    
                if not ret:
                    break
                    
                frame_count += 1
                self.monitor.update()
                
                if 'on_progress' in self.callbacks:
                    self.callbacks['on_progress'](frame_count)

                if is_processing_frame:
                    batch_frames.append(frame)
                    batch_ids.append(frame_count)

                    if len(batch_frames) >= self.batch_size:
                        self._process_and_emit(batch_frames, batch_ids, cfg_analytics)
                        batch_frames, batch_ids = [], []

                if frame_count % 30 == 0:
                    if 'on_performance' in self.callbacks:
                        self.callbacks['on_performance'](self.monitor.get_stats())

            # Дорабатываем остатки батча
            if batch_frames:
                self._process_and_emit(batch_frames, batch_ids, cfg_analytics)

        finally:
            cap.release()
            self.data_logger.close()
            logger.info(f"Обработка {filename} завершена. Всего кадров: {frame_count}")
        
        return True

    def _process_and_emit(self, frames, ids, cfg_analytics):
        if self.batch_size > 1:
            batch_results = self.detector.process_batch(
                frames, 
                frame_ids=ids,
                roi=cfg_analytics.roi,
                staff_zones=cfg_analytics.staff_zones
            )
            # Эмитим только последний результат батча для стат-коллбэка
            if 'on_stats' in self.callbacks and batch_results:
                last_detections, _ = batch_results[-1]
                self.callbacks['on_stats'](last_detections)
        else:
            # Одиночный режим
            detections, active_ids = self.detector.process_frame(
                frames[0], 
                frame_id=ids[0],
                roi=cfg_analytics.roi,
                staff_zones=cfg_analytics.staff_zones
            )
            if 'on_stats' in self.callbacks:
                self.callbacks['on_stats'](detections)

    def stop(self):
        self.running = False
