import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Загрузчик/сохранятор конфигурации из JSON файлов."""

    @staticmethod
    def load_json(filepath: str) -> Optional[dict]:
        """Загрузить конфигурацию из JSON файла."""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Файл конфигурации не найден: {filepath}")
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка загрузки {filepath}: {e}")
            return None

    @staticmethod
    def save_json(filepath: str, data: dict) -> bool:
        """Сохранить конфигурацию в JSON файл."""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            return True
        except IOError as e:
            logger.error(f"Ошибка сохранения {filepath}: {e}")
            return False
