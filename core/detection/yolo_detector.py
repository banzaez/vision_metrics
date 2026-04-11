import logging
import time
import numpy as np
from ultralytics import YOLO
import config
from core.results.frame_result import FrameResult

logger = logging.getLogger(__name__)


class YOLODetector:
    """Обертка над моделью YOLO для обеспечения инференса и детекции объектов."""

    def __init__(self, model_path, device="mps"):
        self.model_path = model_path
        self.device = device
        self._model = None

        self.cfg_yolo = config.settings.yolo
        self.cfg_tracker = config.settings.tracker

    @property
    def model(self):
        if self._model is None:
            logger.info(f"Загрузка YOLO модели: {self.model_path} ({self.device})...")
            self._model = YOLO(self.model_path)
        return self._model

    def detect(self, input_data, frame_id=0):
        """
        Запуск детекции на кадре или батче кадров.

        Args:
            input_data: numpy array (кадр) или list of numpy arrays (батч)
            frame_id: ID кадра для Result

        Returns:
            FrameResult с результатами детекции
        """
        start_time = time.perf_counter()
        
        try:
            if input_data is None:
                return FrameResult.error(frame_id, "Input frame is None")
            
            if not isinstance(input_data, np.ndarray):
                return FrameResult.error(frame_id, f"Invalid input type: {type(input_data)}")
            
            if input_data.size == 0:
                return FrameResult.error(frame_id, "Input frame is empty")
            
            results = self.model.predict(
                input_data,
                device=self.device,
                classes=self.cfg_tracker.classes,
                verbose=False,
                imgsz=self.cfg_yolo.imgsz,
                conf=self.cfg_yolo.conf_threshold,
                iou=self.cfg_yolo.iou_threshold,
                retina_masks=self.cfg_yolo.retina_masks,
                agnostic_nms=self.cfg_yolo.agnostic_nms,
            )
            
            processing_time = (time.perf_counter() - start_time) * 1000
            return FrameResult.ok(frame_id, results, processing_time)
            
        except Exception as e:
            logger.error(f"YOLO detection error on frame {frame_id}: {e}")
            return FrameResult.error(frame_id, str(e))
