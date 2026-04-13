from dataclasses import dataclass


@dataclass
class PathsConfig:
    """Пути к файлам настроек."""

    roi_file: str = 'roi_settings.json'
    """Область интереса (Region of Interest) для детекции."""

    staff_zones_file: str = 'staff_zones.json'
    """Зоны автоматического определения персонала."""

    kpi_zones_file: str = 'kpi_zones.json'
    """Именованные зоны KPI для аналитики консультаций."""

    window_settings_file: str = "window_settings.json"
    """Состояние и геометрия главного окна приложения."""
