from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class IdentificationParams:
    """Общие параметры идентификации объектов."""
    # Порог яркости (0-255), ниже которого одежда считается темной
    black_threshold: int = 30
    # Порог отсечения бликов (V в HSV, 0-255)
    glare_threshold: int = 240
    # Доля темных пикселей, при которой одежда считается темной (0.0 - 1.0)
    dark_ratio_threshold: float = 0.4
    # Длина истории типов для стабилизации классификации (staff/client)
    history_length: int = 300
    # Максимальное количество ID в памяти для истории
    max_tracked_ids: int = 1000

    def __post_init__(self):
        if not (0 <= self.black_threshold <= 255):
            raise ValueError(f"black_threshold must be in [0, 255], got {self.black_threshold}")
        if not (0 <= self.glare_threshold <= 255):
            raise ValueError(f"glare_threshold must be in [0, 255], got {self.glare_threshold}")
        if not (0.0 <= self.dark_ratio_threshold <= 1.0):
            raise ValueError(f"dark_ratio_threshold must be in [0.0, 1.0], got {self.dark_ratio_threshold}")
        if self.history_length < 1:
            raise ValueError(f"history_length must be >= 1, got {self.history_length}")
        if self.max_tracked_ids < 1:
            raise ValueError(f"max_tracked_ids must be >= 1, got {self.max_tracked_ids}")

@dataclass
class RoleParams:
    """Параметры классификации ролей (Персонал / Клиент)."""
    # Минимальное количество кадров для начала оценки роли
    min_eval_frames: int = 5
    # Параметры EMA для вероятности роли
    ema_alpha: float = 0.20
    # Пороги принятия решения по EMA (staff > threshold, client < threshold)
    staff_threshold: float = 0.60
    client_threshold: float = 0.40
    # Инерция (гистерезис): насколько ниже/выше должен быть порог для удержания статуса
    hysteresis: float = 0.15
    # Коэффициенты области торса относительно высоты бокса (0..1)
    torso_top: float = 0.15
    torso_bottom: float = 0.50
    # Порог времени нахождения в зоне персонала (5 сек * ~10 обработанных FPS = 50 кадров)
    staff_zone_threshold_frames: int = 50

    def __post_init__(self):
        if self.min_eval_frames < 1:
            raise ValueError(f"min_eval_frames must be >= 1, got {self.min_eval_frames}")
        if not (0.0 < self.ema_alpha < 1.0):
            raise ValueError(f"ema_alpha must be in (0.0, 1.0), got {self.ema_alpha}")
        if not (0.0 <= self.staff_threshold <= 1.0):
            raise ValueError(f"staff_threshold must be in [0.0, 1.0], got {self.staff_threshold}")
        if not (0.0 <= self.client_threshold <= 1.0):
            raise ValueError(f"client_threshold must be in [0.0, 1.0], got {self.client_threshold}")
        if not (0.0 <= self.hysteresis <= 1.0):
            raise ValueError(f"hysteresis must be in [0.0, 1.0], got {self.hysteresis}")
        if not (0.0 <= self.torso_top <= 1.0):
            raise ValueError(f"torso_top must be in [0.0, 1.0], got {self.torso_top}")
        if not (0.0 <= self.torso_bottom <= 1.0):
            raise ValueError(f"torso_bottom must be in [0.0, 1.0], got {self.torso_bottom}")
        if self.staff_zone_threshold_frames < 1:
            raise ValueError(f"staff_zone_threshold_frames must be >= 1, got {self.staff_zone_threshold_frames}")

@dataclass
class AnalyticsConfig:
    """Группа параметров аналитики."""
    ident: IdentificationParams = field(default_factory=IdentificationParams)
    role: RoleParams = field(default_factory=RoleParams)
    
    # ID камеры для идентификации в логах и данных
    camera_id: str = "CAM_01"
    # Область интереса [x1, y1, x2, y2]
    roi: Optional[List[int]] = None
    # Зоны персонала (список полигонов/боксов)
    staff_zones: List[List[int]] = field(default_factory=list)

