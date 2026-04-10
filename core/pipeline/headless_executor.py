import cv2
import os
import logging
import config
from core.pipeline.orchestrator import DetectorTracker
from core.analytics.data_logger import JSONDataLogger
from utils.monitor import ResourceMonitor

logger = logging.getLogger(__name__)

class HeadlessExecutor:
    """
    Универсальный исполнитель для обработки видео без GUI.
    Может использоваться как в CLI-скриптах, так и внутри VideoWorker.
    """
    def __init__(self, source_path, weights=None, device=None, callbacks=None):
        self.source_path = source_path
        self.weights = weights or config.settings.yolo.weights
        self.device = device or config.settings.system.perf.device
        self.callbacks = callbacks or {} # Словарь функций: on_frame, on_stats, on_progress
        
        self.running = False
        self.detector = None
        self.data_logger = None
        self.monitor = ResourceMonitor()

    def run(self):
        """Запускает полный цикл обработки видео."""
        self.running = True
        
        # 1. Загрузка компонентов
        try:
            cfg_perf = config.settings.system.perf
            cfg_analytics = config.settings.analytics
            
            self.detector = DetectorTracker(
                model_path=self.weights,
                camera_id=cfg_analytics.camera_id,
                device=self.device,
                half=cfg_perf.half
            )
            
            # Определяем имя лога
            filename = os.path.basename(self.source_path)
            json_filename = os.path.splitext(filename)[0] + ".json"
            output_path = os.path.join("data", json_filename)
            
            self.data_logger = JSONDataLogger(output_path=output_path)
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
        self.data_logger.open()
        
        # Настраиваем оркестратор (унифицированная логика)
        self.detector.fps = meta["fps"]
        self.detector.data_logger = self.data_logger
        
        if 'on_duration' in self.callbacks:
            self.callbacks['on_duration'](total_frames)

        frame_count = 0
        logger.info(f"Начало обработки {filename} (Headless Mode)...")

        while self.running:
            is_processing_frame = frame_count % cfg_perf.frame_skip == 0
            
            if is_processing_frame:
                ret, frame = cap.read()
            else:
                ret = cap.grab()
                
            if not ret:
                break
                
            frame_count += 1
            self.monitor.update() # Считаем каждый кадр для честного FPS
            
            # Обновляем прогресс чаще (раз в 1 кадр, tqdm сам оптимизирует отрисовку)
            if 'on_progress' in self.callbacks:
                self.callbacks['on_progress'](frame_count)

            if is_processing_frame:
                # Вся логика логгирования и расчета lifetime теперь внутри process_frame!
                detections, active_ids = self.detector.process_frame(
                    frame, 
                    frame_id=frame_count,
                    roi=cfg_analytics.roi,
                    staff_zones=cfg_analytics.staff_zones
                )
                
                if 'on_stats' in self.callbacks:
                    self.callbacks['on_stats'](detections)
            
            # Метрики ресурсов раз в секунду
            if frame_count % 30 == 0:
                if 'on_performance' in self.callbacks:
                    self.callbacks['on_performance'](self.monitor.get_stats())

        # Завершение
        cap.release()
        self.data_logger.close()
        logger.info(f"Обработка {filename} завершена. Всего кадров: {frame_count}")
        return True

    def stop(self):
        self.running = False
