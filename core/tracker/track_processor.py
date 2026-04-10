import logging
from collections import deque
from core.person_data import PersonData

logger = logging.getLogger(__name__)

class TrackProcessor:
    """Класс для обработки жизненного цикла и бизнес-логики отдельного трека."""

    def __init__(self, camera_id, zone_manager, role_classifier, tracks_storage, history_length):
        self.camera_id = camera_id
        self.zone_manager = zone_manager
        self.role_classifier = role_classifier
        self.tracks = tracks_storage
        self.history_length = history_length

    def process_track(self, obj, boxes, masks_np, input_frame, x_off, y_off, frame_id, timestamp):
        """Обработка одного трека от трекера."""
        # obj format: [x1, y1, x2, y2, track_id, conf, cls, det_ind]
        tx1, ty1, tx2, ty2 = obj[:4]
        track_id = int(obj[4])
        conf = obj[5]
        # 8-й столбец содержит индекс исходной детекции (если есть)
        det_valid = len(obj) > 7 and 0 <= int(obj[7]) < len(boxes)
        det_ind = int(obj[7]) if det_valid else -1

        # 1. Извлечение геометрии и трансформация координат
        if det_ind != -1:
            orig_box = boxes[det_ind]
        else:
            # Если индекса нет, используем предсказание трекера (приводим к int)
            orig_box = (int(tx1), int(ty1), int(tx2), int(ty2))
        
        x1, x2 = int(tx1) + x_off, int(tx2) + x_off
        y1, y2 = int(ty1) + y_off, int(ty2) + y_off

        # 2. Бизнес-логика (зоны и признаки)
        cx, cy = (x1 + x2) // 2, y2
        in_staff_zone = self.zone_manager.is_in_staff_zone(cx, cy)
        is_dark = self.role_classifier.get_is_dark(
            track_id, det_ind, orig_box, input_frame, masks_np if det_ind != -1 else None,
            current_frame_id=frame_id
        )

        # 3. Обновление состояния трека
        td = self._get_or_create_track(track_id, frame_id, timestamp)
        td.zone_frames = td.zone_frames + 1 if in_staff_zone else 0
        
        # Обновление истории координат
        td.prev_bbox = td.last_bbox
        td.last_bbox = (x1, y1, x2, y2)
        td.last_frame_id = frame_id
        
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
