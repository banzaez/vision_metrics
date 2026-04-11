import logging
from collections import OrderedDict
from typing import Dict, Optional, Callable, List

from core.tracking.person_data import PersonData

logger = logging.getLogger(__name__)

class TrackRegistry:
    """
    Умное хранилище треков с поддержкой LRU-эвикции и уведомлений об удалении.
    """
    def __init__(self, max_ids: int):
        self._tracks: Dict[int, PersonData] = OrderedDict()
        self._max_ids = max_ids
        self._on_evict_callbacks: List[Callable[[int], None]] = []

    def add_on_evict_callback(self, callback: Callable[[int], None]):
        """Добавить функцию, которая будет вызвана при удалении трека из памяти."""
        self._on_evict_callbacks.append(callback)

    def get(self, track_id: int) -> Optional[PersonData]:
        return self._tracks.get(track_id)

    def __setitem__(self, key: int, value: PersonData):
        self._tracks[key] = value
        # При установке нового/обновлении перемещаем в конец (LRU)
        self._tracks.move_to_end(key)
        self._check_limit()

    def __getitem__(self, key: int) -> PersonData:
        data = self._tracks[key]
        self._tracks.move_to_end(key)
        return data

    def __contains__(self, key: int) -> bool:
        return key in self._tracks

    def popitem(self, last=True):
        return self._tracks.popitem(last=last)

    def pop(self, key: int, default=None):
        return self._tracks.pop(key, default)

    def move_to_end(self, key: int, last=True):
        if key in self._tracks:
            self._tracks.move_to_end(key, last=last)

    def _check_limit(self):
        """Проверка лимита и эвикция старых треков."""
        while len(self._tracks) > self._max_ids:
            # Popitem(last=False) удаляет старейший элемент (FIFO/LRU)
            tid, _ = self._tracks.popitem(last=False)
            logger.debug(f"[TrackRegistry] Эвикция трека {tid} по лимиту памяти")
            for callback in self._on_evict_callbacks:
                try:
                    callback(tid)
                except Exception as e:
                    logger.error(f"Ошибка в callback эвикции для id={tid}: {e}")

    @property
    def current_ids(self) -> List[int]:
        return list(self._tracks.keys())

    def __len__(self) -> int:
        return len(self._tracks)
