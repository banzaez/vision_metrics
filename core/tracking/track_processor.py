import logging
from .track_manager import TrackManager
from core.analytics.track_analyzer import TrackAnalyzer

logger = logging.getLogger(__name__)


class TrackProcessor:
    """Класс для обработки жизненного цикла и бизнес-логики отдельного трека."""

    def __init__(self, camera_id, zone_manager, role_classifier, tracks_storage, history_length):
        self.camera_id = camera_id
        self.zone_manager = zone_manager
        self.role_classifier = role_classifier
        self.tracks = tracks_storage
        self.history_length = history_length
        
        self._track_manager = TrackManager(camera_id, tracks_storage, history_length)
        self._track_analyzer = TrackAnalyzer(camera_id, zone_manager, role_classifier)

    def process_track(self, obj, boxes, masks_np, input_frame, x_off, y_off, frame_id, timestamp):
        """Обработка одного трека от трекера."""
        tx1, ty1, tx2, ty2 = obj[:4]
        track_id = int(obj[4])
        
        x1, x2 = int(tx1) + x_off, int(tx2) + x_off
        y1, y2 = int(ty1) + y_off, int(ty2) + y_off
        bbox = (x1, y1, x2, y2)

        person_data = self._track_manager.get_or_create(track_id, frame_id, timestamp)
        self._track_manager.update_position(person_data, bbox, frame_id)

        result = self._track_analyzer.analyze(
            person_data=person_data,
            detection=obj,
            input_frame=input_frame,
            masks_np=masks_np,
            frame_id=frame_id,
            start_frame_id=person_data.start_frame
        )

        self._track_manager.finalize(track_id)

        return result
