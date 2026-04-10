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


class ReIDModel(str, Enum):
    """
    Модели Re-ID (Person Re-Identification) для извлечения признаков внешности.
    Позволяют трекеру "узнавать" человека после исчезновения или перекрытия.
    """

    # CLIP_VIT_B_32: [Точность: Экстремальная] [Скорость: Низкая]
    # Тяжелая модель от OpenAI. Видит микро-детали, но сильно нагружает Mac.
    CLIP_VIT_B_32 = "clip_vit_b_32.pt"

    # MOBILENET_V2_X1_4: [Точность: Средняя] [Скорость: Очень высокая]
    # Оптимизирована под мобильные архитектуры, работает очень плавно.
    MOBILENET_V2_X1_4 = "mobilenetv2_x1_4_msmt17.pt"

    # OSNET_IBN_X1_0: [Точность: Максимальная для OSNet] [Скорость: Средняя]
    # ЛУЧШИЙ ВЫБОР: Игнорирует блики от витрин и резкие тени в магазине.
    OSNET_IBN_X1_0 = "osnet_ibn_x1_0_msmt17.pt"

    # OSNET_X0_25: [Точность: Низкая] [Скорость: Ультра]
    # Очень быстрая, но часто путает людей в похожей одежде.
    OSNET_X0_25 = "osnet_x0_25_msmt17.pt"

    # OSNET_X0_5: [Точность: Средняя] [Скорость: Высокая]
    # Хороший вариант, если нужно обрабатывать 3+ камеры одновременно на одном M1.
    OSNET_X0_5 = "osnet_x0_5_msmt17.pt"

    # OSNET_X0_75: [Точность: Средняя+] [Скорость: Выше средней]
    # Облегченная на 25% версия без значительной потери точности.
    OSNET_X0_75 = "osnet_x0_75_msmt17.pt"

    # OSNET_X1_0: [Точность: Высокая] [Скорость: Средняя]
    # Золотой стандарт для ритейла. Обучена на самом сложном датасете MSMT17.
    OSNET_X1_0 = "osnet_x1_0_msmt17.pt"


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
