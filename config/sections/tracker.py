from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from config.trackers.boosttrack import BoostTrackConfig
from config.trackers.botsort import BotSortConfig
from config.trackers.bytetrack import ByteTrackConfig
from config.trackers.deepocsort import DeepOcSortConfig
from config.trackers.hybridsort import HybridSortConfig
from config.trackers.ocsort import OcSortConfig
from config.trackers.sfsort import SFSortConfig
from config.trackers.strongsort import StrongSortConfig
from .reid import CustomReIDConfig


class TrackerType(str, Enum):
    """
    Типы доступных трекеров в BoxMOT.

    Характеристики (Точность, Скорость, Ресурсы):
    - BOOSTTRACK:  [Точность: 10/10] [Скорость: 5/10] [Ресурсы: Высокие] [Re-ID]
    - BOTSORT:     [Точность: 9/10]  [Скорость: 7/10] [Ресурсы: Средние] [Re-ID]
    - BYTETRACK:   [Точность: 6/10]  [Скорость: 10/10] [Ресурсы: Низкие]
    - DEEPOCSORT:  [Точность: 9/10]  [Скорость: 6/10] [Ресурсы: Высокие] [Re-ID]
    - HYBRIDSORT:  [Точность: 8/10]  [Скорость: 6/10] [Ресурсы: Средние] [Re-ID]
    - OCSORT:      [Точность: 8/10]  [Скорость: 8/10] [Ресурсы: Средние]
    - SFSORT:      [Точность: 7/10]  [Скорость: 9/10] [Ресурсы: Низкие]
    - STRONGSORT:  [Точность: 9/10]  [Скорость: 4/10] [Ресурсы: Очень высокие] [Re-ID]
    """

    BOOSTTRACK = "boosttrack"
    BOTSORT = "botsort"
    BYTETRACK = "bytetrack"
    DEEPOCSORT = "deepocsort"
    HYBRIDSORT = "hybridmot"
    OCSORT = "ocsort"
    SFSORT = "sfsort"
    STRONGSORT = "strongsort"


class ReIDModel(str, Enum):
    """
    Библиотека Re-ID моделей для BoxMOT.
    - OSNET_AIN — рекомендуемая: игнорирует фон/блики, фокус на человеке.
    - OSNET_X1_0 — универсальная: баланс точности и FPS.
    - OSNET_X0_25 — минимальная: для 5+ камер одновременно.
    """

    # Максимальная точность
    CLIP_MSMT = "clip_market1501.pt"
    OSNET_AIN = "osnet_ain_x1_0_msmt17.pt"
    HACNN = "hacnn_msmt17.pt"
    RESNET101 = "resnet101_msmt17.pt"

    # Баланс
    OSNET_IBN = "osnet_ibn_x1_0_msmt17.pt"
    OSNET_X1_0 = "osnet_x1_0_msmt17.pt"
    RESNET50_FC512 = "resnet50_fc512_msmt17.pt"
    MLFN = "mlfn_msmt17.pt"

    # Стандартные
    OSNET_MARKET = "osnet_x1_0_market1501.pt"
    OSNET_DUKE = "osnet_x1_0_dukemtmcreid.pt"
    RESNET50_MARKET = "resnet50_market1501.pt"
    CLIP_DUKE = "clip_duke.pt"

    # Легкие
    OSNET_X0_75 = "osnet_x0_75_msmt17.pt"
    OSNET_X0_5 = "osnet_x0_5_msmt17.pt"
    OSNET_X0_25 = "osnet_x0_25_msmt17.pt"
    MOBILENET_V2 = "mobilenetv2_x1_4_msmt17.pt"


@dataclass
class TrackerConfigEntry:
    """Запись конфигурации конкретного трекера."""

    name: str
    """Человекочитаемое название трекера."""

    config: object
    """Объект конфигурации (dataclass)."""


@dataclass
class TrackerRegistry:
    """Реестр доступных трекеров."""

    configs: Dict[TrackerType, TrackerConfigEntry] = field(
        default_factory=lambda: {
            TrackerType.BOOSTTRACK: TrackerConfigEntry(
                name="BoostTrack", config=BoostTrackConfig()
            ),
            TrackerType.BOTSORT: TrackerConfigEntry(
                name="BoTSORT", config=BotSortConfig()
            ),
            TrackerType.BYTETRACK: TrackerConfigEntry(
                name="ByteTrack", config=ByteTrackConfig()
            ),
            TrackerType.DEEPOCSORT: TrackerConfigEntry(
                name="DeepOCSort", config=DeepOcSortConfig()
            ),
            TrackerType.HYBRIDSORT: TrackerConfigEntry(
                name="HybridSort", config=HybridSortConfig()
            ),
            TrackerType.OCSORT: TrackerConfigEntry(
                name="OCSort", config=OcSortConfig()
            ),
            TrackerType.SFSORT: TrackerConfigEntry(
                name="SFSort", config=SFSortConfig()
            ),
            TrackerType.STRONGSORT: TrackerConfigEntry(
                name="StrongSort", config=StrongSortConfig()
            ),
        }
    )

    def get_config(self, tracker_type: TrackerType) -> object:
        """Возвращает объект конфигурации для указанного типа трекера."""
        entry = self.configs.get(tracker_type)
        return entry.config if entry else self.configs[TrackerType.BOTSORT].config

    def get_name(self, tracker_type: TrackerType) -> str:
        """Возвращает человекочитаемое название трекера."""
        entry = self.configs.get(tracker_type)
        return entry.name if entry else "Unknown"


# ==> SETTINGS TRACKER AND REID


@dataclass
class TrackerConfig:
    """
    Конфигурация трекера.
    Выбор типа трекера, Re-ID и базовые настройки.
    """

    type: TrackerType = TrackerType.HYBRIDSORT
    """Активный тип трекера."""

    with_reid: bool = True
    """Использовать ли Re-ID (поддерживается в: BoTSORT, BoostTrack, DeepOCSort, StrongSort, HybridSort)."""

    reid_model: str = ReIDModel.OSNET_X1_0
    """Модель Re-ID (только для: DeepSort, DeepOCSort, StrongSort, HybridSort)."""

    classes: List[int] = field(default_factory=lambda: [0])
    """Список классов для отслеживания ([0] для людей)."""

    custom_reid: CustomReIDConfig = field(default_factory=CustomReIDConfig)
    """Настройки кастомного алгоритма сшивки (CustomReIDStitcher)."""

    registry: TrackerRegistry = field(default_factory=TrackerRegistry, repr=False)
    """Внутренний реестр конфигураций трекеров."""

    @property
    def config(self) -> object:
        """Alias for active_config (backward compatibility)."""
        return self.active_config

    @property
    def model_name(self) -> str:
        """Alias for active_name (backward compatibility)."""
        return self.active_name

    @property
    def active_config(self) -> object:
        """Конфигурация текущего выбранного трекера."""
        return self.registry.get_config(self.type)

    @property
    def active_name(self) -> str:
        """Название текущего трекера."""
        return self.registry.get_name(self.type)
