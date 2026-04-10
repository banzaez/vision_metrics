from collections import OrderedDict
import logging
import time
import numpy as np
import config

from core.analytics.role_classifier import RoleClassifier
from core.analytics.zone_manager import ZoneManager
from core.detection.yolo_detector import YOLODetector
from core.tracking.tracking_service import TrackingService
from core.tracking.track_processor import TrackProcessor
from core.tracking.reid_gallery import ReIDGallery
from core.tracking.reid_stitcher import ReIDStitcher
from core.utils import crop_roi, filter_detections

logger = logging.getLogger(__name__)

class DetectorTracker:
    """Оркестратор трекинга: объединяет детекцию, трекинг и бизнес-логику."""

    def __init__(self, model_path, camera_id="0", device="mps", half=False):
        cfg_ident = config.settings.analytics.ident
        self.camera_id = camera_id

        # Подсистемы
        self.detector = YOLODetector(model_path, device)
        self.tracking_service = TrackingService(device, half)
        self.role_classifier = RoleClassifier()
        self.zone_manager = ZoneManager()

        # Состояние
        self.tracks = OrderedDict()  # track_id -> PersonData
        self._max_total_ids = cfg_ident.max_tracked_ids

        # Процессор треков (бизнес-логика каждого объекта)
        self.track_processor = TrackProcessor(
            camera_id=self.camera_id,
            zone_manager=self.zone_manager,
            role_classifier=self.role_classifier,
            tracks_storage=self.tracks,
            history_length=cfg_ident.history_length
        )

        # Re-ID и склейка треков
        gallery_cfg = config.settings.tracker.gallery
        self.reid_gallery = ReIDGallery(gallery_cfg) if gallery_cfg.enabled else None
        self.stitcher = ReIDStitcher(self.reid_gallery, self.tracks) if self.reid_gallery else None

        self._frame_count = 0
        self.fps = 25.0
        self.data_logger = None
        logger.info("DetectorTracker инициализирован.")

    def process_frame(self, frame, frame_id, timestamp=None, roi=None, staff_zones=None):
        """Основной цикл обработки одного кадра."""
        self.zone_manager.update_staff_mask(staff_zones or [], frame.shape)
        input_frame, x_off, y_off = crop_roi(frame, roi)
        current_ts = timestamp if timestamp is not None else time.time()

        results = self.detector.detect(input_frame)
        detections, active_ids = self._analyze_results(results[0], input_frame, x_off, y_off, frame_id, current_ts)
        
        self._finalize_step()
        return detections, active_ids

    def process_batch(self, frames, frame_ids, timestamps=None, roi=None, staff_zones=None):
        """Пакетная обработка кадров (batch mode)."""
        if not frames: return []
        self.zone_manager.update_staff_mask(staff_zones or [], frames[0].shape)

        processed_inputs = [crop_roi(f, roi)[0] for f in frames]
        offsets = [crop_roi(f, roi)[1:] for f in frames]
        ts_list = timestamps if timestamps is not None else [time.time()] * len(frames)

        results = self.detector.detect(processed_inputs)
        batch_output = []

        for res, inp_frame, (x_off, y_off), f_id, ts in zip(results, processed_inputs, offsets, frame_ids, ts_list):
            detections, active_ids = self._analyze_results(res, inp_frame, x_off, y_off, f_id, ts)
            self._post_process_metrics(detections, f_id, ts)
            batch_output.append((detections, active_ids))
            self._finalize_step()

        return batch_output

    def _analyze_results(self, result, input_frame, x_off, y_off, current_frame_id, timestamp):
        """Связующее звено между YOLO, трекером и бизнес-логикой."""
        if not self.tracking_service.tracker or not result.boxes or len(result.boxes) == 0:
            return self._handle_fallback(result, x_off, y_off, current_frame_id), set()

        # 1. Фильтрация детекций
        boxes, confs, cls, masks = self._prepare_yolo_data(result, input_frame)
        if len(boxes) == 0: return [], set()

        # 2. Трекинг
        tracked_objects = self.tracking_service.update(boxes, confs, cls, input_frame)
        if tracked_objects is None or len(tracked_objects) == 0: return [], set()

        # 3. Re-ID и Stitching
        if self.stitcher:
            self.stitcher.update(tracked_objects, self.tracking_service.tracker)

        # 4. Обработка каждого объекта
        detections, active_ids = [], set()
        for obj in tracked_objects:
            det = self.track_processor.process_track(
                obj, boxes, masks, input_frame, x_off, y_off, current_frame_id, timestamp
            )
            if det:
                # Применяем алиас ID если трек был склеен
                if self.reid_gallery:
                    det["track_id"] = self.reid_gallery.apply_alias(det["track_id"])
                
                detections.append(det)
                active_ids.add(det["track_id"])

        self._post_process_metrics(detections, current_frame_id)
        return detections, active_ids

    def _prepare_yolo_data(self, result, input_frame):
        """Извлечение и базовая фильтрация данных из YOLO."""
        boxes = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
        cls = result.boxes.cls.cpu().numpy()
        masks = result.masks.data.cpu().numpy() if result.masks is not None else None

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
        if not result.boxes: return detections
        
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
        
        # Периодическая очистка кэша ReID
        if self.reid_gallery and self._frame_count % 60 == 0:
            self.reid_gallery.cleanup()

        # LRU Очистка старых треков
        while len(self.tracks) > self._max_total_ids:
            tid, _ = self.tracks.popitem(last=False)
            self.role_classifier.remove_track_data(tid)
