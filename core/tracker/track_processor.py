import logging
from collections import deque
from .person_data import PersonData

logger = logging.getLogger(__name__)

class TrackProcessor:
    """Класс для обработки жизненного цикла и бизнес-логики отдельного трека."""

    def __init__(self, camera_id, zone_manager, role_classifier, tracks_storage, history_length):
        self.camera_id = camera_id
        self.zone_manager = zone_manager
        self.role_classifier = role_classifier
        self.tracks = tracks_storage
        self.history_length = history_length

    def process_match(self, match, track_map, boxes, masks_np, input_frame, x_off, y_off, frame_id, timestamp):
        """Обработка одного вхождения (match) от трекера."""
        track_id, original_idx, iou = match
        obj = track_map.get(track_id)
        if obj is None:
            return None

        # 1. Извлечение геометрии и трансформация координат
        tx1, ty1, tx2, ty2, _, conf, _ = obj[:7]
        orig_box = boxes[original_idx] if original_idx != -1 else (tx1, ty1, tx2, ty2)
        
        x1, x2 = int(tx1) + x_off, int(tx2) + x_off
        y1, y2 = int(ty1) + y_off, int(ty2) + y_off

        # 2. Бизнес-логика (зоны и признаки)
        cx, cy = (x1 + x2) // 2, y2
        in_staff_zone = self.zone_manager.is_in_staff_zone(cx, cy)
        is_dark = self.role_classifier.get_is_dark(
            track_id, original_idx, orig_box, input_frame, masks_np if original_idx != -1 else None,
            current_frame_id=frame_id
        )

        # 3. Обновление состояния трека
        td = self._get_or_create_track(track_id, frame_id, timestamp)
        td.zone_frames = td.zone_frames + 1 if in_staff_zone else 0
        td.last_bbox, td.last_frame_id = (x1, y1, x2, y2), frame_id
        
        # 4. Классификация роли по истории (EMA)
        td.history.append(is_dark)
        p_type, type_conf, type_conf_cal, new_ema = self.role_classifier.classify_person_type(
            is_dark, td.ema, len(td.history), in_staff_zone=in_staff_zone,
            zone_frames=td.zone_frames, prev_type=td.last_type
        )
        td.ema, td.last_type = new_ema, p_type
        
        # Обновляем позицию в LRU-кэше
        self.tracks.move_to_end(track_id)

        return {
            "track_id": track_id,
            "camera_id": self.camera_id,
            "frame_id": frame_id,
            "bbox": (x1, y1, x2, y2),
            "timestamp": timestamp,
            "conf": float(conf),
            "type": p_type,
            "type_confidence": type_conf,
            "type_confidence_calibrated": type_conf_cal,
            "lifetime_frames": frame_id - td.start_frame,
            "is_ghost": False
        }

    def _get_or_create_track(self, track_id, current_frame_id, timestamp):
        """Получение существующего или создание нового объекта PersonData."""
        if track_id not in self.tracks:
            self.tracks[track_id] = PersonData(
                track_id=track_id,
                camera_id=self.camera_id,
                start_frame=current_frame_id,
                last_frame_id=current_frame_id,
                start_timestamp=timestamp,
                history=deque(maxlen=self.history_length)
            )
        return self.tracks[track_id]
