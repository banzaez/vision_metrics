import json
import os
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from .system import SystemConfig
from .yolo import YOLOParams
from .tracker import TrackerConfig
from .paths import PathsConfig
from .analytics import AnalyticsConfig
from .events import ConfigBus, ConfigChangeEvent


logger = logging.getLogger(__name__)


class ConfigSection:
    """Base class for config sections with event notification."""

    def set(self, key: str, value: Any) -> None:
        """Set a value and notify subscribers."""
        old_value = getattr(self, key, None)
        object.__setattr__(self, key, value)
        ConfigBus.notify(ConfigChangeEvent(
            section=self.__class__.__name__,
            key=key,
            old_value=old_value,
            new_value=value
        ))


@dataclass
class AppConfig:
    """
    Основной менеджер конфигурации Vision Metrics.
    Группирует все настройки по категориям.
    """
    system: SystemConfig = field(default_factory=SystemConfig)
    yolo: YOLOParams = field(default_factory=YOLOParams)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)

    def _set_nested(self, section_name: str, key: str, value: Any) -> None:
        """Set nested config value with event notification."""
        section = getattr(self, section_name, None)
        if section is None:
            return
        old_value = getattr(section, key, None)
        object.__setattr__(section, key, value)
        ConfigBus.notify(ConfigChangeEvent(
            section=section_name,
            key=key,
            old_value=old_value,
            new_value=value
        ))

    def set(self, section: str, key: str, value: Any) -> None:
        """Public API for setting config values with events."""
        self._set_nested(section, key, value)

    def load(self):
        """Загрузка динамических настроек из JSON файлов."""
        # ROI
        if os.path.exists(self.paths.roi_file):
            try:
                with open(self.paths.roi_file, 'r', encoding='utf-8') as f:
                    self.analytics.roi = json.load(f)
            except Exception as e:
                logger.warning(f"Не удалось загрузить ROI из {self.paths.roi_file}: {e}")
            
        # Staff Zones
        if os.path.exists(self.paths.staff_zones_file):
            try:
                with open(self.paths.staff_zones_file, 'r', encoding='utf-8') as f:
                    self.analytics.staff_zones = json.load(f)
            except Exception as e:
                logger.warning(f"Не удалось загрузить зоны персонала из {self.paths.staff_zones_file}: {e}")

# Создаем глобальный экземпляр настроек
settings = AppConfig()
settings.load()
