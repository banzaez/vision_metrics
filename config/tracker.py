from config.trackers.base import ReIDModel
from dataclasses import dataclass, field
from typing import List
from config.trackers.base import TrackerType, BaseTrackerParams


@dataclass
class TrackerConfig(BaseTrackerParams):
    """
    Конфигурация трекера.
    Здесь осуществляется только выбор типа и базовые настройки.
    Вся логика перенесена в config.trackers.base
    """

    # Выбор активного трекера
    type: TrackerType = TrackerType.HYBRIDSORT

    # Использовать ли Re-ID
    # Поддерживается в: BoTSORT, BoostTrack, DeepOCSort, StrongSort, HybridSort
    with_reid: bool = True

    # Выбор модели Re-ID
    # Только для: DeepSort, DeepOCSort, StrongSort, HybridSort
    reid_model: str = ReIDModel.OSNET_X1_0

    # Список классов для отслеживания ([0] для людей)
    classes: List[int] = field(default_factory=lambda: [0])
