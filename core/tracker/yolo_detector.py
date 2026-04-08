import logging
from ultralytics import YOLO
import config

logger = logging.getLogger(__name__)

class YOLODetector:
    """Обертка над моделью YOLO для обеспечения инференса и детекции объектов."""
    
    def __init__(self, model_path, device="mps"):
        self.model_path = model_path
        self.device = device
        self._model = None
        
        # Кэширование конфигов
        self.cfg_yolo = config.settings.yolo
        self.cfg_tracker = config.settings.tracker

    @property
    def model(self):
        if self._model is None:
            logger.info(f"Загрузка YOLO модели: {self.model_path} ({self.device})...")
            self._model = YOLO(self.model_path)
        return self._model

    def detect(self, input_data):
        """
        Запуск детекции на кадре или батче кадров.
        
        Args:
            input_data: numpy array (кадр) или list of numpy arrays (батч)
            
        Returns:
            list of Results: Результаты детекции YOLO
        """
        return self.model.predict(
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
