import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .sections.system import SystemConfig
from .sections.yolo import YOLOParams
from .sections.tracker import TrackerConfig
from .sections.paths import PathsConfig
from .sections.analytics import AnalyticsConfig
from .events import ConfigBus, ConfigChangeEvent
from .loader import ConfigLoader

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """
    Единый менеджер конфигурации Vision Metrics.

    Использование:
        from config import settings

        # Прямой доступ (чтение)
        conf = settings.yolo.conf_threshold
        device = settings.system.perf.device

        # Прямой доступ (запись с уведомлением)
        settings.set('yolo.conf_threshold', 0.5)

        # Загрузка из JSON
        settings.load_from_file('my_config.json')

        # Сохранение в JSON
        settings.save_to_file('my_config.json')
    """

    system: SystemConfig = field(default_factory=SystemConfig)
    yolo: YOLOParams = field(default_factory=YOLOParams)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)

    # ─── Public API ──────────────────────────────────────────────────────

    def get(self, dotted_path: str) -> Any:
        """
        Получить значение по точечному пути.

        Примеры:
            settings.get('yolo.conf_threshold')
            settings.get('system.perf.device')
            settings.get('tracker.type')
        """
        parts = dotted_path.split(".")
        obj = self
        for part in parts:
            obj = getattr(obj, part, None)
            if obj is None:
                raise KeyError(f"Config path '{dotted_path}' not found")
        return obj

    @staticmethod
    def _find_nested_attr(obj: Any, key: str) -> Any | None:
        """Recursively search for a key in nested dataclass attributes."""
        if hasattr(obj, key):
            return getattr(obj, key)
        for attr_name in dir(obj):
            if attr_name.startswith("_"):
                continue
            attr = getattr(obj, attr_name, None)
            if attr is not None and hasattr(attr, "__dataclass_fields__"):
                result = AppConfig._find_nested_attr(attr, key)
                if result is not None:
                    return result
        return None

    @staticmethod
    def _set_nested_attr(obj: Any, key: str, value: Any) -> tuple[bool, Any, str]:
        """
        Recursively find and set a nested attribute.
        Returns (found, parent_obj, attr_name) or (False, None, None).
        """
        if hasattr(obj, key):
            old_value = getattr(obj, key)
            setattr(obj, key, value)
            return True, obj, key
        for attr_name in dir(obj):
            if attr_name.startswith("_"):
                continue
            attr = getattr(obj, attr_name, None)
            if attr is not None and hasattr(attr, "__dataclass_fields__"):
                found, parent, actual_key = AppConfig._set_nested_attr(attr, key, value)
                if found:
                    return True, parent, actual_key
        return False, None, None

    def set(
        self, section_or_path: str, key_or_value: Any = None, value: Any = None
    ) -> None:
        """
        Установить значение с уведомлением подписчиков.

        Поддерживает два формата (для обратной совместимости):

        Новый (рекомендуемый):
            settings.set('yolo.conf_threshold', 0.5)
            settings.set('system.perf.device', 'cuda')

        Старый (cli.py):
            settings.set('yolo', 'conf_threshold', 0.5)
            settings.set('system', 'frame_interval', 2)  # авто-поиск вложенного
        """
        # Detect calling style
        if value is not None and key_or_value is not None:
            # Old style: set(section, key, value)
            section_name = section_or_path
            key = key_or_value
            new_value = value
        else:
            # New style: set('section.key', value)
            parts = section_or_path.rsplit(".", 1)
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid config path '{section_or_path}'. Expected: 'section.key'"
                )
            section_name, key = parts
            new_value = key_or_value

        # Navigate to section
        section = self
        for part in section_name.split("."):
            section = getattr(section, part, None)
            if section is None:
                raise KeyError(f"Config section '{section_name}' not found")

        # Try direct attribute, then nested search
        if hasattr(section, key):
            old_value = getattr(section, key)
            setattr(section, key, new_value)
            event_section_name = section_name
        else:
            found, parent, actual_key = self._set_nested_attr(section, key, new_value)
            if not found:
                raise AttributeError(
                    f"Key '{key}' not found in section '{section_name}'"
                )
            old_value = getattr(parent, actual_key)
            setattr(parent, actual_key, new_value)
            # Build full path for event
            event_section_name = section_name

        ConfigBus.notify(
            ConfigChangeEvent(
                section=event_section_name,
                key=key,
                old_value=old_value,
                new_value=new_value,
            )
        )

    def to_dict(self) -> dict:
        """Сериализовать конфигурацию в словарь."""
        return asdict(self)

    def update_from_dict(self, data: dict) -> None:
        """Обновить конфигурацию из словаря."""
        for section_name, section_data in data.items():
            section = getattr(self, section_name, None)
            if section is None:
                logger.warning(f"Unknown config section: {section_name}")
                continue
            if isinstance(section_data, dict):
                self._update_nested(section, section_data)
            else:
                setattr(section, section_name, section_data)

    def _update_nested(self, obj: Any, data: dict) -> None:
        """Рекурсивно обновить вложенные объекты."""
        for key, value in data.items():
            if hasattr(obj, key):
                attr = getattr(obj, key)
                if isinstance(value, dict) and hasattr(attr, "__dataclass_fields__"):
                    self._update_nested(attr, value)
                else:
                    setattr(obj, key, value)

    # ─── Loading / Saving ────────────────────────────────────────────────

    def load(self) -> None:
        """Загрузка динамических настроек из JSON файлов (ROI, зоны)."""
        self._load_json_file(self.paths.roi_file, "analytics.roi")
        self._load_json_file(self.paths.staff_zones_file, "analytics.staff_zones")

    def _load_json_file(self, filepath: str, target_path: str) -> None:
        """Загрузить значение из JSON файла по указанному пути."""
        path = Path(filepath)
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                value = json.load(f)
            self.set(target_path, value)
        except Exception as e:
            logger.warning(f"Не удалось загрузить {target_path} из {filepath}: {e}")

    def load_from_file(self, filepath: str) -> None:
        """Полная загрузка конфигурации из JSON файла."""
        data = ConfigLoader.load_json(filepath)
        if data:
            self.update_from_dict(data)
            logger.info(f"Конфигурация загружена из {filepath}")

    def save_to_file(self, filepath: str) -> None:
        """Сохранить текущую конфигурацию в JSON файл."""
        ConfigLoader.save_json(filepath, self.to_dict())
        logger.info(f"Конфигурация сохранена в {filepath}")


# ─── Global singleton ────────────────────────────────────────────────────

settings = AppConfig()
settings.load()
