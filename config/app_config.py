import json
import os
import logging
from dataclasses import dataclass, field
from .system import SystemConfig
from .yolo import YOLOParams
from .tracker import TrackerParams
from .paths import PathsConfig
from .analytics import AnalyticsConfig


logger = logging.getLogger(__name__)

@dataclass
class AppConfig:
    """
    Основной менеджер конфигурации Vision Metrics.
    Группирует все настройки по категориям.
    """
    system: SystemConfig = field(default_factory=SystemConfig)
    yolo: YOLOParams = field(default_factory=YOLOParams)
    tracker: TrackerParams = field(default_factory=TrackerParams)
    paths: PathsConfig = field(default_factory=PathsConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)

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
