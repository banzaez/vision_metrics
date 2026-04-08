from dataclasses import dataclass

@dataclass
class PathsConfig:
    """Пути к файлам настроек."""
    # Область интереса (Region of Interest) для детекции
    roi_file: str = 'roi_settings.json'
    # Зоны автоматического определения персонала
    staff_zones_file: str = 'staff_zones.json'
    # Состояние и геометрия главного окна приложения
    window_settings_file: str = "window_settings.json"
    # Папка с конфигурациями трекеров
    trackers_dir: str = "config/trackers"
