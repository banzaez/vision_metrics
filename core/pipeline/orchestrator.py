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
from core.utils import crop_roi, filter_detections

logger = logging.getLogger(__name__)


class DetectorTracker:
    """Оркестратор трекинга объектов: объединяет детекцию, трекинг и бизнес-логику (роли, зоны)."""

    def __init__(self, model_path, camera_id="0", device="mps", half=False):
        cfg_ident = config.settings.analytics.ident

        # Идентификация источника
        self.camera_id = camera_id

        # Подсистемы
        self.detector = YOLODetector(model_path, device)
        self.tracking_service = TrackingService(device, half)
        self.role_classifier = RoleClassifier()
        self.zone_manager = ZoneManager()

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

        # Re-ID Gallery (ID Stitcher) — надстройка для устранения смены ID
        gallery_cfg = config.settings.tracker.gallery
        self.reid_gallery: ReIDGallery | None = (
            ReIDGallery(gallery_cfg) if gallery_cfg.enabled else None
        )
        if self.reid_gallery:
            logger.info("[ReIDGallery] Включена (порог=%.2f, ttl=%.0fs)",
                        gallery_cfg.similarity_threshold, gallery_cfg.max_age_seconds)
        else:
            logger.info("[ReIDGallery] Отключена.")

        # Множество ID, которые были активны на предыдущем кадре
        self._prev_active_ids: set[int] = set()

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
            return self._handle_fallback(result, x_off, y_off, current_frame_id), active_ids

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

        # 3. Re-ID Gallery: обновляем галерею и применяем alias_map
        if self.reid_gallery is not None:
            self._update_reid_gallery(tracked_objects, confs)

        # 4. Обработка каждого отслеженного объекта через TrackProcessor
        for obj in tracked_objects:
            det = self.track_processor.process_track(
                obj, boxes, masks_np, input_frame, x_off, y_off, current_frame_id, timestamp
            )
            if det:
                # Применяем alias_map — подменяем ID если есть совпадение
                if self.reid_gallery is not None:
                    canonical_id = self.reid_gallery.apply_alias(det["track_id"])
                    if canonical_id != det["track_id"]:
                        det["track_id"] = canonical_id
                        det["id_stitched"] = True
                detections.append(det)
                active_ids.add(det["track_id"])

        return detections, active_ids

    def _update_reid_gallery(
        self,
        tracked_objects: np.ndarray,
        confs: np.ndarray,
    ) -> None:
        """
        Обновляет Re-ID галерею:
          1. Извлекает эмбеддинги из BoxMOT-трекера.
          2. Для активных треков → вызывает gallery.feed_active().
          3. Для «исчезнувших» треков → вызывает gallery.on_track_lost().
          4. Для «новых» треков → вызывает gallery.match_new_track() и обновляет alias_map.
          5. Периодически очищает устаревшие записи (cleanup).
        """
        gallery = self.reid_gallery

        # Эмбеддинги из внутреннего состояния трекера {track_id: np.ndarray}
        tracker_embeddings = gallery.extract_embeddings_from_tracker(
            self.tracking_service.tracker
        )

        # Текущие активные ID и их боксы
        current_active: dict[int, tuple] = {}
        for obj in tracked_objects:
            tid = int(obj[4])
            bbox = (float(obj[0]), float(obj[1]), float(obj[2]), float(obj[3]))
            current_active[tid] = bbox

            # Кормим галерею эмбеддингом (если есть)
            emb = tracker_embeddings.get(tid)
            if emb is not None:
                # conf: берём из самого tracked_objects (столбец 5)
                tr_conf = float(obj[5]) if len(obj) > 5 else 0.5
                gallery.feed_active(tid, emb, tr_conf, bbox)

        current_ids = set(current_active.keys())

        # Треки, которые были активны на прошлом кадре, но исчезли сейчас
        lost_ids = self._prev_active_ids - current_ids
        for lost_id in lost_ids:
            # Последний бокс берём из PersonData если он есть
            person = self.tracks.get(lost_id)
            last_bbox = person.last_bbox if person and person.last_bbox else (0, 0, 0, 0)
            gallery.on_track_lost(lost_id, last_bbox)

        # Новые треки — ищем совпадение в dead_pool
        new_ids = current_ids - self._prev_active_ids
        for new_id in new_ids:
            # Пропускаем если уже есть алиас
            if new_id in gallery.alias_map:
                continue
            emb = tracker_embeddings.get(new_id)
            if emb is None:
                continue
            bbox = current_active[new_id]
            old_id = gallery.match_new_track(new_id, emb, bbox)
            if old_id is not None:
                gallery.alias_map[new_id] = old_id
                # Переносим PersonData со старого ID если нужно (объединение истории)
                self._stitch_person_data(new_id, old_id)

        self._prev_active_ids = current_ids

        # Периодическая очистка galery
        if self._frame_count % 60 == 0:
            gallery.cleanup()

    def _stitch_person_data(self, new_id: int, old_id: int) -> None:
        """
        Объединяет PersonData: копирует историю старого ID на новый,
        чтобы аналитика видела непрерывный трек.
        """
        old_data = self.tracks.get(old_id)
        new_data = self.tracks.get(new_id)

        if old_data is None or old_data is new_data:
            return

        if new_data is None:
            # Новый ID ещё не попал в tracks — просто переиспользуем старый объект
            self.tracks[new_id] = old_data
            return

        # Объединяем: переносим историю EMA старого ID на новый
        new_data.ema = old_data.ema
        new_data.start_frame = old_data.start_frame
        new_data.start_timestamp = old_data.start_timestamp
        
        # Сливаем историю (используем копию списка, чтобы избежать RuntimeError)
        # Добавляем старую историю в начало новой, сохраняя порядок
        old_history = list(old_data.history)
        for h in reversed(old_history):
            new_data.history.appendleft(h)
        
        logger.debug(f"[ReIDGallery] PersonData склеены: new_id={new_id} ← old_id={old_id} (history_len={len(new_data.history)})")



    def _handle_fallback(self, result, x_off, y_off, frame_id):
        detections = []
        if result.boxes is not None:
            for i, box in enumerate(result.boxes.xyxy.cpu().numpy()):
                x1, y1, x2, y2 = map(int, box)
                # Генерируем уникальный временный ID для этого кадра, чтобы избежать конфликтов
                temp_id = -(frame_id * 1000 + i + 1)
                detections.append({
                    "track_id": temp_id,
                    "camera_id": self.camera_id,
                    "frame_id": frame_id,
                    "bbox": (x1 + x_off, y1 + y_off, x2 + x_off, y2 + y_off),
                    "conf": float(result.boxes.conf[i]),
                    "type": "unknown",
                    "is_ghost": True
                })
        return detections

    def _cleanup_lru(self):
        """Очистка старых треков для экономии памяти."""
        while len(self.tracks) > self._max_total_ids:
            tid, _ = self.tracks.popitem(last=False)
            self.role_classifier.remove_track_data(tid)
