from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from config.trackers.boosttrack import BoostTrackConfig
from config.trackers.botsort import BotSortConfig
from config.trackers.bytetrack import ByteTrackConfig
from config.trackers.deepocsort import DeepOcSortConfig
from config.trackers.hybridsort import HybridSortConfig
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


class ReIDModel(str, Enum):
    """
    Полная библиотека Re-ID моделей для BoxMOT.
    - MSMT17: Лучший датасет (126к фото), макс. точность.
    - AIN/IBN: Технологии борьбы с шумом и светом.
    - FC512: Улучшенная детализация признаков.
    """

    # --- ТЯЖЕЛАЯ АРТИЛЛЕРИЯ (Максимальное удержание ID) ---
    CLIP_MSMT = "clip_market1501.pt"            # Vision Transformer. Лучшая для узнавания после долгого исчезновения.
    OSNET_AIN = "osnet_ain_x1_0_msmt17.pt"      # Attention Instance Norm. Игнорирует фон/блики, фокус на человеке. (РЕКОМЕНДУЕМАЯ)
    HACNN = "hacnn_msmt17.pt"                   # Harmonious Attention. Ищет уникальные детали (часы, логотипы, прическа).
    RESNET101 = "resnet101_msmt17.pt"           # Максимально глубокая сеть. Высокая точность, очень низкая скорость.

    # --- ЗОЛОТОЙ СТАНДАРТ (Баланс точности и FPS) ---
    OSNET_IBN = "osnet_ibn_x1_0_msmt17.pt"      # Устойчива к смене освещения (яркие витрины vs тени).
    OSNET_X1_0 = "osnet_x1_0_msmt17.pt"         # Универсальная модель. Баланс для ритейла.
    RESNET50_FC512 = "resnet50_fc512_msmt17.pt" # Создает длинный дескриптор. Помогает отличать людей в похожей одежде.
    MLFN = "mlfn_msmt17.pt"                     # Многоуровневый анализ. Хорошо работает при смене ракурса (наклон над витриной).

    # --- СРЕДНЯЯ ТОЧНОСТЬ (Старые датасеты) ---
    OSNET_MARKET = "osnet_x1_0_market1501.pt"   # Стандарт для простых сцен.
    OSNET_DUKE = "osnet_x1_0_dukemtmcreid.pt"   # Оптимизирована под разные углы обзора камер.
    RESNET50_MARKET = "resnet50_market1501.pt"  # Классический ResNet50.
    CLIP_DUKE = "clip_duke.pt"                  # Трансформер, обученный на данных Duke.

    # --- ЛЕГКИЕ МОДЕЛИ (Для повышения FPS на M1 Pro) ---
    OSNET_X0_75 = "osnet_x0_75_msmt17.pt"       # Облегченная на 25% без большой потери точности.
    OSNET_X0_5 = "osnet_x0_5_msmt17.pt"         # В 2 раза быстрее. Для обработки нескольких камер.
    OSNET_X0_25 = "osnet_x0_25_msmt17.pt"       # Минимальный вес. Для 5+ камер одновременно.
    MOBILENET_V2 = "mobilenetv2_x1_4_msmt17.pt" # Архитектура для мобильных CPU. Максимальная плавность видео.


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
