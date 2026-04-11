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
            "ema": self.ema,
        }
