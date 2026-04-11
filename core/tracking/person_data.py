from dataclasses import dataclass, field
from collections import deque
from typing import Tuple, Optional, Deque

@dataclass
class PersonData:
    """Контейнер для хранения всех необходимых данных об одном отслеживаемом человеке."""
    track_id: int
    camera_id: str
    start_frame: int
    last_frame_id: int
    start_timestamp: float
    
    # История классификации (is_dark) — ограничена maxlen=300 по умолчанию для защиты от OOM
    history: Deque[bool] = field(default_factory=lambda: deque(maxlen=300))
    
    # EMA для вероятности роли (staff/client)
    ema: float = 0.5
    
    # Геометрия
    last_bbox: Optional[Tuple[int, int, int, int]] = None
    prev_bbox: Optional[Tuple[int, int, int, int]] = None
    
    # Состояние
    zone_frames: int = 0
    last_type: str = "CLIENT"
    
    def to_dict(self, frame_id, timestamp):
        """Преобразование текущего состояния в формат для сохранения/логов."""
        return {
            "track_id": self.track_id,
            "camera_id": self.camera_id,
            "frame_id": frame_id,
            "bbox": self.last_bbox,
            "timestamp": timestamp,
            "type": self.last_type,
            "ema": self.ema
        }

    def merge_from(self, other: 'PersonData') -> None:
        """
        Сливает данные из другого объекта (обычно старого фрагмента трека) в текущий.
        Помогает сохранить непрерывную историю при склейке (Re-ID Stitching).
        """
        if other is None or other is self:
            return

        # 1. Наследование временных меток (берем самое раннее)
        self.start_frame = min(self.start_frame, other.start_frame)
        self.start_timestamp = min(self.start_timestamp, other.start_timestamp)

        # 2. Слияние истории классификации (старые данные в начало очереди)
        # extendleft работает за O(k), reversed за O(k). Итого O(k) вместо O(k^2)
        if other.history:
            self.history.extendleft(reversed(other.history))

        # 3. Перенос накопленных метрик
        self.ema = other.ema
        self.zone_frames += other.zone_frames

        # Примечание: last_bbox, prev_bbox и last_type обычно оставляем от нового трека,
        # так как они отражают текущее визуальное состояние.
