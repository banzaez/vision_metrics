import logging
from collections import deque

logger = logging.getLogger(__name__)


class TrackManager:
    """Управление жизненным циклом треков - создание, получение, обновление базовых данных."""

    def __init__(self, camera_id, tracks_storage, history_length):
        self.camera_id = camera_id
        self.tracks = tracks_storage
        self.history_length = history_length

    def get_or_create(self, track_id, frame_id, timestamp):
        """Получение существующего или создание нового объекта PersonData."""
        from .person_data import PersonData
        
        if track_id not in self.tracks:
            self.tracks[track_id] = PersonData(
                track_id=track_id,
                camera_id=self.camera_id,
                start_frame=frame_id,
                last_frame_id=frame_id,
                start_timestamp=timestamp,
                history=deque(maxlen=self.history_length)
            )
        return self.tracks[track_id]

    def update_position(self, person_data, bbox, frame_id):
        """Обновление позиции трека."""
        person_data.prev_bbox = person_data.last_bbox
        person_data.last_bbox = bbox
        person_data.last_frame_id = frame_id
        person_data._dirty = True

    def finalize(self, track_id):
        """Переместить трек в конец LRU кэша только если данные изменились."""
        if track_id in self.tracks:
            pd = self.tracks[track_id]
            if pd._dirty:
                self.tracks.move_to_end(track_id)
                pd._dirty = False