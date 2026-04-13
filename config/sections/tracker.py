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
    ТИПЫ ДОСТУПНЫХ ТРЕКЕРОВ В BoxMOT (Актуально на 2026 год):

    Общая иерархия выбора:
    Точность (SOTA) -> BOOSTTRACK / DEEPOCSORT
    Баланс (Best)  -> BOTSORT / HYBRIDSORT
    Скорость (FPS) -> BYTETRACK / OCSORT / SFSORT

    Подробные характеристики:
    -------------------------------------------------------------------------------------------
    | ТРЕКЕР      | ТОЧНОСТЬ | СКОРОСТЬ | РЕСУРСЫ | Re-ID | ОСОБЕННОСТИ                        |
    |-------------|:--------:|:--------:|:-------:|:-----:|------------------------------------|
    | BOOSTTRACK  |  10/10   |   5/10   | Высокие |   +   | SOTA 2026. Лучший при окклюзиях.   |
    | BOTSORT     |   9/10   |   7/10   | Средние |   +   | Индустриальный стандарт. Стабилен. |
    | DEEPOCSORT  |   9/10   |   6/10   | Высокие |   +   | Хорош при резких сменах траекторий.|
    | STRONGSORT  |   9/10   |   2/10   | Оч. Вык |   +   | Тяжелый/Медленный. Устаревающий.   |
    | HYBRIDSORT  |   8/10   |   6/10   | Средние |   +   | Эффективен при плохом освещении.   |
    | OCSORT      |   8/10   |   8/10   | Средние |   -   | Чистая геометрия, без внешности.   |
    | BYTETRACK   |   7/10   |  10/10   | Низкие  |   -   | Макс. FPS. Для простого подсчета.  |
    | SFSORT      |   6/10   |   9/10   | Низкие  |   -   | Ультра-лайт. Для слабых CPU.       |
    -------------------------------------------------------------------------------------------

    ПРАВКИ И ПОЯСНЕНИЯ:

    1. BOOSTTRACK (10/10): Лидер за счет 'Boosting' весов между геометрией и Re-ID.
       Рекомендуется для ювелирных магазинов, где критично не терять ID за прилавками.

    2. BOTSORT (9/10): Самый надежный "универсал". Имеет встроенную компенсацию
       движения камеры (GMC). Если камера вибрирует или чуть смещается — он не паникует.

    3. BYTETRACK (10/10 Speed): Самый быстрый, так как не тратит время на Re-ID сравнение.
       В 2026 году его точность выросла (7/10) благодаря нейросетям YOLOv11+, которые
       дают очень четкие детекции.

    4. STRONGSORT (2/10 Speed): Основная правка. В современных реалиях BoxMOT он
       неоправданно медленный. На Apple M1 Pro может выдавать всего 5-8 FPS.
       Использовать только если FPS не имеет значения.

    5. OCSORT (8/10): Идеален для объектов с нелинейным движением. Если люди в магазине
       часто и резко меняют направление, он отработает лучше, чем ByteTrack.
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
    Библиотека Re-ID весов для BoxMOT (Актуально на 2026 год).
    
    Словарь суффиксов:
    - msmt17: Самый большой датасет (лучшая точность в реальных условиях).
    - market1501/duke: Устаревшие датасеты (ниже точность).
    - fc512: Увеличенный вектор признаков (лучше различает похожую одежду).
    """

    # --- ГРУППА 1: МАКСИМАЛЬНАЯ ТОЧНОСТЬ (SOTA) ---
    # Предназначены для сложных сцен с перекрытиями и бликами. Медленнее остальных.
    CLIP_MSMT = "clip_market1501.pt"            # [SOTA] Vision Transformer. Лучшее понимание атрибутов одежды.
    OSNET_AIN = "osnet_ain_x1_0_msmt17.pt"      # [TOP] Адаптивное внимание. Игнорирует фон/блики. Идеально для ювелирки.
    HACNN = "hacnn_msmt17.pt"                   # Фокус на частях тела (голова, торс, ноги). Хорошо, если виден не весь человек.
    RESNET101 = "resnet101_msmt17.pt"           # Очень глубокая сеть. Высокая точность, но очень тяжелая для M1 Pro.

    # --- ГРУППА 2: БАЛАНС (РЕКОМЕНДУЕМЫЕ) ---
    # Оптимальный выбор для работы в реальном времени (15-30 FPS).
    OSNET_IBN = "osnet_ibn_x1_0_msmt17.pt"      # Устойчива к смене освещения и резким теням.
    OSNET_X1_0 = "osnet_x1_0_msmt17.pt"         # Универсальный стандарт. Хорошая точность при среднем весе.
    RESNET50_FC512 = "resnet50_fc512_msmt17.pt" # Детальный дескриптор. Помогает, когда много людей в похожей форме.
    MLFN = "mlfn_msmt17.pt"                     # Многоуровневый анализ. Помогает при сильной смене ракурса камеры.

    # --- ГРУППА 3: СТАНДАРТНЫЕ (ДЛЯ ТЕСТОВ) ---
    # Обучены на простых датасетах. Не рекомендуются для боевых задач в ритейле.
    OSNET_MARKET = "osnet_x1_0_market1501.pt"   # Базовая OSNet.
    OSNET_DUKE = "osnet_x1_0_dukemtmcreid.pt"   # Оптимизирована под разные углы камер (DukeMTMC).
    RESNET50_MARKET = "resnet50_market1501.pt"  # Классический ResNet50.
    CLIP_DUKE = "clip_duke.pt"                  # Вариант CLIP для специфических ракурсов.

    # --- ГРУППА 4: ЛЕГКИЕ (ULTRA FAST) ---
    # Если нужно обрабатывать 5+ камер одновременно или выжать 60+ FPS.
    OSNET_X0_75 = "osnet_x0_75_msmt17.pt"       # На 25% быстрее x1.0 при минимальной потере точности.
    OSNET_X0_5 = "osnet_x0_5_msmt17.pt"         # В 2 раза быстрее x1.0. Хороший выбор для мультипотока.
    OSNET_X0_25 = "osnet_x0_25_msmt17.pt"       # Ультра-лайт. Для слабых CPU или огромного количества камер.
    MOBILENET_V2 = "mobilenetv2_x1_4_msmt17.pt" # Мобильная архитектура. Максимальная скорость инференса.


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
