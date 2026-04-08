from dataclasses import dataclass, field
from typing import Dict
from enum import Enum

from config.trackers.botsort import BotSortConfig
from config.trackers.bytetrack import ByteTrackConfig

class TrackerType(str, Enum):
    """Типы доступных трекеров."""
    BOTSORT = "botsort"
    BYTETRACK = "bytetrack"


@dataclass
class TrackerConfigEntry:
    """Запись конфигурации конкретного трекера."""
    name: str          # Человекочитаемое название трекера
    config: object     # Объект конфигурации (dataclass)


@dataclass
class TrackerRegistry:
    """Реестр доступных трекеров."""
    # Словарь {TrackerType: TrackerConfigEntry}
    configs: Dict[TrackerType, TrackerConfigEntry] = field(default_factory=lambda: {
        TrackerType.BOTSORT: TrackerConfigEntry(
            name="BoTSORT",
            config=BotSortConfig()
        ),
        TrackerType.BYTETRACK: TrackerConfigEntry(
            name="ByteTrack",
            config=ByteTrackConfig()
        ),
    })


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
