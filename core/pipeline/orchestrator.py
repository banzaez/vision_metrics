import logging
import time
import numpy as np
import config

from core.analytics.role_classifier import RoleClassifier
from core.analytics.zone_manager import ZoneManager
from core.detection.yolo_detector import YOLODetector
from core.tracking.tracking_service import TrackingService
from core.tracking.track_processor import TrackProcessor
from core.tracking.track_registry import TrackRegistry
from core.tracking.reid_stitcher import CustomReIDStitcher
from core.utils import crop_roi, filter_detections

logger = logging.getLogger(__name__)

class DetectorTracker:
    """Оркестратор трекинга: объединяет детекцию, трекинг и бизнес-логику."""

    def __init__(self, model_path, camera_id="0", device="mps", half=False, callbacks=None):
        self.callbacks = callbacks or {}
        cfg_ident = config.settings.analytics.ident
        self.camera_id = camera_id

        # 1. Основные подсистемы
        self.detector = YOLODetector(model_path, device)
        self.tracking_service = TrackingService(device, half)
        self.role_classifier = RoleClassifier()
        self.zone_manager = ZoneManager()

        # 2. Хранилище треков с автоматической очисткой зависимых кэшей
        self.tracks = TrackRegistry(max_ids=cfg_ident.max_tracked_ids)

        # Привязываем очистку кэшей к эвикции трека
        self.tracks.add_on_evict_callback(self.role_classifier.remove_track_data)

        # 3. Процессор треков (бизнес-логика)
        self.track_processor = TrackProcessor(
            camera_id=self.camera_id,
            zone_manager=self.zone_manager,
            role_classifier=self.role_classifier,
            tracks_storage=self.tracks,
            history_length=cfg_ident.history_length
        )

        # 4. Кастомная сшивка треков по внешнему виду (CustomReIDStitcher)
        cfg_custom = config.settings.tracker.custom_reid
        self.reid_stitcher = CustomReIDStitcher(
            threshold=cfg_custom.threshold,
            gallery_size=cfg_custom.gallery_size,
            ema_alpha=cfg_custom.ema_alpha,
            stats_callback_interval=cfg_custom.stats_callback_interval,
        )
        # Пробрасываем ReID модель из основного трекера (если она там есть)
        if hasattr(self.tracking_service.tracker, 'model'):
            self.reid_stitcher.model = self.tracking_service.tracker.model

        self._frame_count = 0
        self.fps = 25.0
        self.data_logger = None
        logger.info("DetectorTracker инициализирован с использованием TrackRegistry.")

    def process_frame(self, frame, frame_id, timestamp=None, roi=None, staff_zones=None):
        """Основной цикл обработки одного кадра."""
        self.zone_manager.update_staff_mask(staff_zones or [], frame.shape)
        input_frame, x_off, y_off = crop_roi(frame, roi)
        current_ts = timestamp if timestamp is not None else time.time()

        frame_result = self.detector.detect(input_frame, frame_id)
        
        if not frame_result.success:
            logger.warning(f"Detection failed on frame {frame_id}: {frame_result.error}")
            return [], set()
        
        if not frame_result.detections or len(frame_result.detections) == 0:
            return [], set()
        
        detections, active_ids = self._analyze_results(frame_result.detections[0], input_frame, x_off, y_off, frame_id, current_ts)
        
        self._finalize_step()
        return detections, active_ids

    def process_batch(self, frames, frame_ids, timestamps=None, roi=None, staff_zones=None):
        """Пакетная обработка кадров (batch mode)."""
        if not frames:
            return []
        self.zone_manager.update_staff_mask(staff_zones or [], frames[0].shape)

        processed_inputs = [crop_roi(f, roi)[0] for f in frames]
        offsets = [crop_roi(f, roi)[1:] for f in frames]
        ts_list = timestamps if timestamps is not None else [time.time()] * len(frames)

        batch_input = processed_inputs[0] if len(processed_inputs) == 1 else processed_inputs
        batch_frame_id = frame_ids[0] if len(frame_ids) == 1 else 0
        results = self.detector.detect(batch_input, batch_frame_id)
        
        if not results.success:
            logger.warning(f"Batch detection failed: {results.error}")
            return []
        
        detection_results = results.detections
        if not detection_results:
            return []
        
        batch_output = []

        for res, inp_frame, (x_off, y_off), f_id, ts in zip(detection_results, processed_inputs, offsets, frame_ids, ts_list):
            detections, active_ids = self._analyze_results(res, inp_frame, x_off, y_off, f_id, ts)
            batch_output.append((detections, active_ids))
            self._finalize_step()

        return batch_output

    def _analyze_results(self, result, input_frame, x_off, y_off, current_frame_id, timestamp):
        """Связующее звено между YOLO, трекером и бизнес-логикой."""
        if not self.tracking_service.tracker:
            if not result.boxes or len(result.boxes) == 0:
                return [], set()
            return self._handle_fallback(result, x_off, y_off, current_frame_id), set()

        masks = None
        if not result.boxes or len(result.boxes) == 0:
            boxes = np.zeros((0, 4), dtype=np.float64)
            confs = np.zeros((0,), dtype=np.float64)
            cls = np.zeros((0,), dtype=np.float64)
        else:
            boxes, confs, cls, masks = self._prepare_yolo_data(result, input_frame)

        tracked_objects = self.tracking_service.update(boxes, confs, cls, input_frame)
        if tracked_objects is None:
            tracked_objects = np.zeros((0, 8), dtype=np.float64)

        # Кастомная сшивка треков (если включена в конфиге)
        if tracked_objects.shape[0] > 0 and config.settings.tracker.custom_reid.enabled:
            tracked_objects = self.reid_stitcher.process(
                tracked_objects, input_frame, 
                self.tracking_service.tracker,
                event_callback=self.callbacks.get('on_reid')
            )

        if tracked_objects.shape[0] == 0:
            return [], set()

        # Обработка каждого объекта
        detections, active_ids = [], set()
        for obj in tracked_objects:
            # Обработка бизнес-логики (зоны, роль, история)
            det = self.track_processor.process_track(
                obj, boxes, masks, input_frame, x_off, y_off, current_frame_id, timestamp
            )
            
            if det:
                detections.append(det)
                active_ids.add(det["track_id"])

        self._post_process_metrics(detections, current_frame_id)
        return detections, active_ids

    def _prepare_yolo_data(self, result, input_frame):
        """Извлечение и базовая фильтрация данных из YOLO."""
        try:
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            cls = result.boxes.cls.cpu().numpy()
        except Exception as e:
            logger.warning(f"Failed to extract boxes from YOLO result: {e}")
            return np.zeros((0, 4), dtype=np.float64), np.zeros((0,), dtype=np.float64), np.zeros((0,), dtype=np.float64), None
        
        try:
            masks = result.masks.data.cpu().numpy() if result.masks is not None else None
            if masks is not None:
                if not isinstance(masks, np.ndarray):
                    masks = None
                elif masks.ndim != 3:
                    logger.warning(f"Invalid masks shape: {masks.shape}")
                    masks = None
                elif masks.shape[0] != len(boxes):
                    logger.warning(f"Masks count ({masks.shape[0]}) != boxes count ({len(boxes)})")
                    masks = None
        except Exception as e:
            logger.warning(f"Failed to process masks: {e}")
            masks = None
        
        h, w = input_frame.shape[:2]
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, w)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, h)
        return filter_detections(boxes, confs, cls, masks)

    def _post_process_metrics(self, detections, frame_id):
        """Расчет времени жизни и логирование."""
        for det in detections:
            l_frames = det.get("lifetime_frames", 0)
            det["lifetime"] = l_frames / self.fps if self.fps > 0 else 0

        if self.data_logger:
             self.data_logger.log_frame(frame_id, detections)

    def _handle_fallback(self, result, x_off, y_off, frame_id):
        """Обработка детекций без треков (если трекер выключен или сбоит)."""
        detections = []
        if not result.boxes:
            return detections
        
        for i, box in enumerate(result.boxes.xyxy.cpu().numpy()):
            x1, y1, x2, y2 = map(int, box)
            detections.append({
                "track_id": -(frame_id * 1000 + i + 1), # Уникальный негативный ID
                "camera_id": self.camera_id,
                "frame_id": frame_id,
                "bbox": (x1 + x_off, y1 + y_off, x2 + x_off, y2 + y_off),
                "conf": float(result.boxes.conf[i]),
                "type": "RAW"
            })
        return detections

    def _finalize_step(self):
        """Очистка ресурсов и инкремент счетчиков после каждого кадра."""
        self._frame_count += 1

        # Примечание: Эвикция старых PersonData теперь происходит 
        # автоматически внутри TrackRegistry (self.tracks) при каждом добавлении.
