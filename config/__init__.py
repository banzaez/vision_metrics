"""
Конфигурация Vision Metrics.

Основной API:
    from config import settings

    # Чтение
    conf = settings.yolo.conf_threshold
    device = settings.system.perf.device

    # Запись (с уведомлением)
    settings.set('yolo.conf_threshold', 0.5)

    # Загрузка/сохранение
    settings.load_from_file('my_config.json')
    settings.save_to_file('my_config.json')

События:
    from config import ConfigBus, ConfigChangeEvent
    ConfigBus.subscribe(lambda e: print(e))
"""

from .app_config import settings, AppConfig
from .events import ConfigBus, ConfigChangeEvent
from .loader import ConfigLoader

__all__ = [
    "settings",
    "AppConfig",
    "ConfigBus",
    "ConfigChangeEvent",
    "ConfigLoader",
]
