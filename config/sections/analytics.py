from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class IdentificationParams:
    """Общие параметры идентификации объектов."""

    black_threshold: int = 30
    """Порог яркости (0-255), ниже которого одежда считается темной."""

    glare_threshold: int = 240
    """Порог отсечения бликов (V в HSV, 0-255)."""

    dark_ratio_threshold: float = 0.4
    """Доля темных пикселей, при которой одежда считается темной (0.0 - 1.0)."""

    history_length: int = 300
    """Длина истории типов для стабилизации классификации (staff/client)."""

    max_tracked_ids: int = 1000
    """Максимальное количество ID в памяти для истории."""


@dataclass
class RoleParams:
    """Параметры классификации ролей (Персонал / Клиент)."""

    min_eval_frames: int = 5
    """Минимальное количество кадров для начала оценки роли."""

    ema_alpha: float = 0.20
    """Параметр EMA для вероятности роли."""

    staff_threshold: float = 0.60
    """Порог EMA для определения как персонал (staff > threshold)."""

    client_threshold: float = 0.40
    """Порог EMA для определения как клиент (client < threshold)."""

    hysteresis: float = 0.15
    """Инерция (гистерезис): насколько ниже/выше должен быть порог для удержания статуса."""

    torso_top: float = 0.15
    """Коэффициент верхней области торса относительно высоты бокса (0..1)."""

    torso_bottom: float = 0.50
    """Коэффициент нижней области торса относительно высоты бокса (0..1)."""

    staff_zone_threshold_frames: int = 50
    """Порог времени нахождения в зоне персонала (5 сек * ~10 FPS = 50 кадров)."""


@dataclass
class AnalyticsConfig:
    """Группа параметров аналитики."""

    ident: IdentificationParams = field(default_factory=IdentificationParams)
    role: RoleParams = field(default_factory=RoleParams)

    camera_id: str = "CAM_01"
    """ID камеры для идентификации в логах и данных."""

    roi: Optional[List[int]] = None
    """Область интереса [x1, y1, x2, y2]."""

    staff_zones: List[List[int]] = field(default_factory=list)
    """Зоны персонала (список полигонов/боксов)."""

    kpi_zones: dict = field(default_factory=dict)
    """Именованные зоны KPI для аналитики консультаций {имя: [(x1,y1), ...]}."""
