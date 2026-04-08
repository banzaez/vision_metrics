from collections import OrderedDict
import logging
import time
import numpy as np
import config

from .role_classifier import RoleClassifier
from .zone_manager import ZoneManager
from .mask_matcher import MaskMatcher
from .yolo_detector import YOLODetector
from .tracking_service import TrackingService
from .track_processor import TrackProcessor
from .utils import crop_roi, filter_detections

logger = logging.getLogger(__name__)


class DetectorTracker:
    """Оркестратор трекинга объектов: объединяет детекцию, трекинг и бизнес-логику (роли, зоны)."""

    def __init__(self, model_path, camera_id="0", device="mps"):
        cfg_ident = config.settings.analytics.ident

        # Идентификация источника
        self.camera_id = camera_id

        # Подсистемы
        self.detector = YOLODetector(model_path, device)
        self.tracking_service = TrackingService(device)
        self.role_classifier = RoleClassifier()
        self.zone_manager = ZoneManager()
        self.mask_matcher = MaskMatcher()

        # Состояние и история
        self.tracks = OrderedDict()  # track_id -> PersonData
        self._history_length = cfg_ident.history_length
        self._max_total_ids = cfg_ident.max_tracked_ids

        # Инициализация процессора треков
        self.track_processor = TrackProcessor(
            camera_id=self.camera_id,
            zone_manager=self.zone_manager,
            role_classifier=self.role_classifier,
            tracks_storage=self.tracks,
            history_length=self._history_length
        )

        self._frame_count = 0
        self._last_staff_zones = None
        self._last_frame_shape = None
        logger.info("DetectorTracker (Orchestrator) инициализирован.")

    def _maybe_update_zone_mask(self, staff_zones, frame_shape):
        """Обновление маски зон при изменении конфигурации или разрешения."""
        staff_zones = staff_zones or []
        if (staff_zones != self._last_staff_zones or frame_shape != self._last_frame_shape):
            self.zone_manager.update_staff_mask(staff_zones, frame_shape)
            self._last_staff_zones = list(staff_zones) if staff_zones else []
            self._last_frame_shape = frame_shape

    def process_frame(self, frame, frame_id, timestamp=None, roi=None, staff_zones=None):
        self._maybe_update_zone_mask(staff_zones, frame.shape)
        input_frame, x_off, y_off = crop_roi(frame, roi)
        
        # Если timestamp не передан, используем системное время
        current_ts = timestamp if timestamp is not None else time.time()

        results = self.detector.detect(input_frame)
        detections, active_ids = self._analyze_results(results[0], input_frame, x_off, y_off, frame_id, current_ts)
        
        self._cleanup_lru()
        self._frame_count += 1
        return detections, active_ids

    def process_batch(self, frames, frame_ids, timestamps=None, roi=None, staff_zones=None):
        if not frames:
            return []
        self._maybe_update_zone_mask(staff_zones, frames[0].shape)

        processed_inputs, offsets = [], []
        for frame in frames:
            inp, x, y = crop_roi(frame, roi)
            processed_inputs.append(inp)
            offsets.append((x, y))

        results = self.detector.detect(processed_inputs)
        ts_list = timestamps if timestamps is not None else [time.time()] * len(frames)

        batch_output = []
        for res, inp_frame, (x_off, y_off), f_id, ts in zip(results, processed_inputs, offsets, frame_ids, ts_list):
            batch_output.append(self._analyze_results(res, inp_frame, x_off, y_off, f_id, ts))
            self._frame_count += 1

        self._cleanup_lru()
        return batch_output

    def _analyze_results(self, result, input_frame, x_off, y_off, current_frame_id, timestamp):
        """Интегрирует результаты детекции с трекером и классификацией."""
        detections, active_ids = [], set()

        if self.tracking_service.tracker is None or result.boxes is None or len(result.boxes) == 0:
            return self._handle_fallback(result, x_off, y_off), active_ids

        # 1. Получение и фильтрация данных YOLO
        boxes = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
        cls = result.boxes.cls.cpu().numpy()
        masks_np = result.masks.data.cpu().numpy() if result.masks is not None else None

        h_f, w_f = input_frame.shape[:2]
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, w_f)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, h_f)
        boxes, confs, cls, masks_np = filter_detections(boxes, confs, cls, masks_np)

        if len(boxes) == 0:
            return detections, active_ids

        # 2. Обновление трекера
        tracked_objects = self.tracking_service.update(boxes, confs, cls, input_frame)

        if tracked_objects is None or len(tracked_objects) == 0:
            return detections, active_ids

        # 3. Сопоставление масок
        matches = self.mask_matcher.match_masks(tracked_objects, boxes, masks_np)
        track_map = {int(obj[4]): obj for obj in tracked_objects}

        # 4. Обработка каждого отслеженного объекта через TrackProcessor
        for match in matches:
            det = self.track_processor.process_match(
                match, track_map, boxes, masks_np, input_frame, x_off, y_off, current_frame_id, timestamp
            )
            if det:
                detections.append(det)
                active_ids.add(det["track_id"])

        return detections, active_ids



    def _handle_fallback(self, result, x_off, y_off):
        detections = []
        if result.boxes is not None:
            for i, box in enumerate(result.boxes.xyxy.cpu().numpy()):
                x1, y1, x2, y2 = map(int, box)
                detections.append({
                    "track_id": -(i + 1), "bbox": (x1 + x_off, y1 + y_off, x2 + x_off, y2 + y_off),
                    "conf": float(result.boxes.conf[i]), "type": "unknown", "is_ghost": False
                })
        return detections

    def _cleanup_lru(self):
        """Очистка старых треков для экономии памяти."""
        while len(self.tracks) > self._max_total_ids:
            tid, _ = self.tracks.popitem(last=False)
            self.role_classifier.remove_track_data(tid)
