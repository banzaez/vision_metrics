from typing import Dict, Set, Tuple
import logging
import numpy as np
from core.tracking.person_data import PersonData
from core.tracking.reid_gallery import ReIDGallery

logger = logging.getLogger(__name__)

class ReIDStitcher:
    """
    Класс-координатор для обработки ReID и 'склейки' прерванных треков.
    Отвечает за взаимодействие между трекером, галереей эмбеддингов и данными PersonData.
    """
    def __init__(self, gallery: ReIDGallery, person_tracks: Dict[int, PersonData]):
        self.gallery = gallery
        self.tracks = person_tracks
        self._prev_active_ids: Set[int] = set()
        self._missing_counts: Dict[int, int] = {}
        self._grace_period = 3 # кадра ожидания перед помещением в dead_pool

    def update(self, tracked_objects: np.ndarray, tracker: object):
        """
        Обновляет галерею и применяет логику склейки ID.
        """
        if not self.gallery:
            return

        # 1. Извлечение эмбеддингов
        tracker_embeddings = self.gallery.extract_embeddings_from_tracker(tracker)

        # 2. Обработка текущих активных треков
        current_active: Dict[int, Tuple[float, float, float, float]] = {}
        for obj in tracked_objects:
            tid = int(obj[4])
            bbox = (float(obj[0]), float(obj[1]), float(obj[2]), float(obj[3]))
            current_active[tid] = bbox

            emb = tracker_embeddings.get(tid)
            if emb is not None:
                tr_conf = float(obj[5]) if len(obj) > 5 else 0.5
                self.gallery.feed_active(tid, emb, tr_conf, bbox)

        current_ids = set(current_active.keys())

        # 3. Обработка исчезнувших треков (lost) c GRACE PERIOD
        # Те, кто были, но исчезли в этом кадре
        lost_now = self._prev_active_ids - current_ids
        for tid in lost_now:
            self._missing_counts[tid] = self._missing_counts.get(tid, 0) + 1
        
        # Если трек вернулся — забываем про него
        for tid in current_ids:
            self._missing_counts.pop(tid, None)

        # Если трек отсутствует слишком долго — фиксируем потерю
        to_finalize = [tid for tid, count in self._missing_counts.items() if count >= self._grace_period]
        for tid in to_finalize:
            person = self.tracks.get(tid)
            last_bbox = person.last_bbox if person and person.last_bbox else (0, 0, 0, 0)
            self.gallery.on_track_lost(tid, last_bbox)
            self._missing_counts.pop(tid)

        # 4. Обработка новых треков (match and stitch)
        new_ids = current_ids - self._prev_active_ids
        for new_id in new_ids:
            if new_id in self.gallery.alias_map:
                continue
            
            emb = tracker_embeddings.get(new_id)
            if emb is None:
                continue
            
            bbox = current_active[new_id]
            old_id = self.gallery.match_new_track(new_id, emb, bbox)
            if old_id is not None:
                self.gallery.alias_map[new_id] = old_id
                self._stitch_person_data(new_id, old_id)

        self._prev_active_ids = current_ids

    def _stitch_person_data(self, new_id: int, old_id: int) -> None:
        """Объединяет историю PersonData старого и нового трека."""
        old_data = self.tracks.get(old_id)
        new_data = self.tracks.get(new_id)

        if old_data is None or old_data is new_data:
            return

        if new_data is None:
            self.tracks[new_id] = old_data
            return

        # Наследование параметров
        new_data.ema = old_data.ema
        new_data.zone_frames = old_data.zone_frames
        new_data.start_frame = old_data.start_frame
        new_data.start_timestamp = old_data.start_timestamp
        
        # Слияние истории (appendleft с конца старого списка)
        old_history = list(old_data.history)
        for h in reversed(old_history):
            new_data.history.appendleft(h)
        
        logger.debug(f"[ReIDStitcher] Склейка ID: {new_id} <- {old_id}")
