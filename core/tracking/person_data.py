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
    current_zone: Optional[str] = None
    last_type: str = "CLIENT"
    _dirty: bool = True

    @property
    def is_staff(self) -> bool:
        return self.last_type.upper() == "STAFF"

    @property
    def center(self) -> Tuple[float, float]:
        if not self.last_bbox:
            return (0.0, 0.0)
        return ((self.last_bbox[0] + self.last_bbox[2]) / 2, 
                (self.last_bbox[1] + self.last_bbox[3]) / 2)

    def update_position(self, bbox: Tuple[int, int, int, int], frame_id: int):
        self.prev_bbox = self.last_bbox
        self.last_bbox = bbox
        self.last_frame_id = frame_id
        self._dirty = True

    def to_dict(self, timestamp):
        """Преобразование текущего состояния в формат для сохранения/логов."""
        return {
            "track_id": self.track_id,
            "camera_id": self.camera_id,
            "frame_id": self.last_frame_id,
            "bbox": self.last_bbox,
            "timestamp": timestamp,
            "type": self.last_type,
            "zone": self.current_zone,
            "ema": self.ema,
        }
