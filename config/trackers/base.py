from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from config.trackers.boosttrack import BoostTrackConfig
from config.trackers.botsort import BotSortConfig
from config.trackers.bytetrack import ByteTrackConfig
from config.trackers.deepocsort import DeepOcSortConfig
from config.trackers.hybridmot import HybridSortConfig
from config.trackers.ocsort import OcSortConfig
from config.trackers.sfsort import SFSortConfig
from config.trackers.strongsort import StrongSortConfig


class TrackerType(str, Enum):
    """
    Типы доступных трекеров в BoxMOT.

    Характеристики (Точность, Скорость, Ресурсы):
    - Точность: Удержание ID при перекрытиях и похожей одежде.
    - Скорость: FPS на Apple Silicon (M1 Pro).
    - Ресурсы: Нагрузка на GPU/CPU и использование Re-ID моделей.
    """

    # BOOST-TRACK: [Точность: 10/10] [Скорость: 5/10] [Ресурсы: Высокие] [Re-ID]
    # Максимальное удержание ID. Корректирует неточности рамок YOLO. Идеально для ювелирки.
    BOOSTTRACK = "boosttrack"

    # BOT-SORT: [Точность: 9/10] [Скорость: 7/10] [Ресурсы: Средние] [Re-ID]
    # Универсальный стандарт. Использует Re-ID и компенсацию движения камеры.
    BOTSORT = "botsort"

    # BYTE-TRACK: [Точность: 6/10] [Скорость: 10/10] [Ресурсы: Низкие]
    # Самый быстрый. Работает только по геометрии (без Re-ID). Идеален для 60+ FPS.
    BYTETRACK = "bytetrack"

    # DEEP-OC-SORT: [Точность: 9/10] [Скорость: 6/10] [Ресурсы: Высокие] [Re-ID]
    # Улучшенный OC-SORT с визуальными признаками. Отличен при длительных перекрытиях.
    DEEPOCSORT = "deepocsort"

    # HYBRID-MOT: [Точность: 8/10] [Скорость: 6/10] [Ресурсы: Средние] [Re-ID]
    # Гибридный подход с учетом уверенности детектора и дополнительных признаков объекта.
    HYBRIDSORT = "hybridmot"

    # OC-SORT: [Точность: 8/10] [Скорость: 8/10] [Ресурсы: Средние]
    # Ориентирован на траектории. Лучший при хаотичном движении и резких поворотах.
    OCSORT = "ocsort"

    # SF-SORT: [Точность: 7/10] [Скорость: 9/10] [Ресурсы: Низкие]
    # "Легкое" зрение. Быстрее чем BoTSORT, но надежнее ByteTrack за счет мини-эмбеддингов.
    SFSORT = "sfsort"

    # STRONG-SORT: [Точность: 9/10] [Скорость: 4/10] [Ресурсы: Очень высокие] [Re-ID]
    # Глубокая аналитика внешности. Очень стабилен, но требует много вычислительной мощности.
    STRONGSORT = "strongsort"


class ReIDModel:
    """
    Модели Re-ID (Person Re-Identification) для извлечения признаков внешности.
    Позволяют трекеру "узнавать" человека после исчезновения или перекрытия.
    """

    # --- ТЯЖЕЛАЯ АРТИЛЛЕРИЯ (SOTA) ---

    # CLIP_MARKET1501: [Точность: Экстремальная] [Скорость: Низкая]
    # Основана на трансформерах. Лучшее понимание контекста (одежда, атрибуты).
    CLIP = "clip_market1501.pt"

    # OSNET_AIN_X1_0: [Точность: Ультра] [Скорость: Средняя]
    # Включает Attention Instance Normalization. Игнорирует фон, фокусируясь на человеке.
    # Идеальна для ювелирных магазинов со сложным визуальным шумом.
    OSNET_AIN_X1_0 = "osnet_ain_x1_0_msmt17.pt"

    # RESNET50_MSMT17: [Точность: Высокая] [Скорость: Ниже средней]
    # Классическая глубокая сеть. Очень стабильные признаки, но тяжелее OSNet.
    RESNET50 = "resnet50_msmt17.pt"

    # RESNET101_MSMT17: [Точность: Очень высокая] [Скорость: Низкая]
    # Максимально глубокая версия ResNet для самых сложных сценариев детекции.
    RESNET101 = "resnet101_msmt17.pt"

    # --- СПЕЦИАЛИЗИРОВАННЫЕ И ГИБРИДНЫЕ ---

    # MLFN: [Точность: Средняя+] [Скорость: Средняя]
    # Multi-Level Factorisation Network. Извлекает признаки на разных уровнях иерархии.
    MLFN = "mlfn_msmt17.pt"

    # HACNN: [Точность: Высокая] [Скорость: Средняя]
    # Harmonious Attention CNN. Совместно обучается вниманию к мягким и жестким признакам.
    HACNN = "hacnn_msmt17.pt"

    # LMBN_N: [Точность: Средняя+] [Скорость: Высокая]
    # Lightweight Multi-Branch Network. Хорошая альтернатива OSNet по скорости.
    LMBN_N = "lmbn_n_market.pt"

    # --- ТВОИ ТЕКУЩИЕ МОДЕЛИ ---

    # CLIP_VIT_B_32: Тяжелая модель от OpenAI (официальная версия).
    CLIP_VIT_B_32 = "clip_vit_b_32.pt"

    # MOBILENET_V2_X1_4: Оптимизирована под мобильные архитектуры.
    MOBILENET_V2_X1_4 = "mobilenetv2_x1_4_msmt17.pt"

    # OSNET_IBN_X1_0: ЛУЧШИЙ ВЫБОР. Игнорирует блики и резкие тени.
    OSNET_IBN_X1_0 = "osnet_ibn_x1_0_msmt17.pt"

    # OSNET_X1_0: Золотой стандарт для ритейла.
    OSNET_X1_0 = "osnet_x1_0_msmt17.pt"

    # Облегченные версии OSNet
    OSNET_X0_75 = "osnet_x0_75_msmt17.pt"
    OSNET_X0_5 = "osnet_x0_5_msmt17.pt"
    OSNET_X0_25 = "osnet_x0_25_msmt17.pt"


@dataclass
class TrackerConfigEntry:
    """Запись конфигурации конкретного трекера."""

    name: str  # Человекочитаемое название трекера
    config: object  # Объект конфигурации (dataclass)


@dataclass
class TrackerRegistry:
    """Реестр доступных трекеров."""

    # Словарь {TrackerType: TrackerConfigEntry}
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


@dataclass
class BaseTrackerParams:
    """Базовая логика параметров трекера."""

    type: TrackerType = TrackerType.BOTSORT
    registry: TrackerRegistry = field(default_factory=TrackerRegistry, repr=False)

    @property
    def config(self) -> object:
        """Возвращает объект конфигурации для текущего выбранного трекера."""
        entry = self.registry.configs.get(self.type)
        if entry:
            return entry.config
        return self.registry.configs[TrackerType.BOTSORT].config

    @property
    def model_name(self) -> str:
        """Возвращает человекочитаемое название модели трекера."""
        entry = self.registry.configs.get(self.type)
        return entry.name if entry else "Unknown"
