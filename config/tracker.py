from dataclasses import dataclass, field
from typing import List
from config.trackers.base import TrackerType, BaseTrackerParams


@dataclass
class TrackerParams(BaseTrackerParams):
    """
    Конфигурация трекера.
    Здесь осуществляется только выбор типа и базовые настройки.
    Вся логика перенесена в config.trackers.base
    """
    # Выбор активного трекера
    type: TrackerType = TrackerType.BYTETRACK

    # Список классов для отслеживания ([0] для людей)
    classes: List[int] = field(default_factory=lambda: [0])
