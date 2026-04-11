"""Система событий конфигурации для реактивного обновления компонентов."""

from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable


@dataclass(frozen=True)
class ConfigChangeEvent:
    """Событие изменения конфигурации."""

    section: str
    """Имя секции (например 'yolo', 'system.perf')."""

    key: str
    """Имя ключа (например 'conf_threshold', 'device')."""

    old_value: Any
    """Предыдущее значение."""

    new_value: Any
    """Новое значение."""


class ConfigBus:
    """
    Шина событий конфигурации.

    Подписчики получают уведомления при изменении любого параметра.

    Пример:
        from config import ConfigBus, ConfigChangeEvent

        def on_change(event: ConfigChangeEvent):
            print(f"{event.section}.{event.key}: {event.old_value} -> {event.new_value}")

        ConfigBus.subscribe(on_change)
    """

    _subscribers: list[Callable[[ConfigChangeEvent], None]] = []
    _lock: Lock = Lock()

    @classmethod
    def subscribe(cls, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """Подписаться на события конфигурации."""
        with cls._lock:
            cls._subscribers.append(callback)

    @classmethod
    def unsubscribe(cls, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """Отписаться от событий."""
        with cls._lock:
            cls._subscribers.remove(callback)

    @classmethod
    def notify(cls, event: ConfigChangeEvent) -> None:
        """Уведомить всех подписчиков о событии."""
        with cls._lock:
            subscribers = list(cls._subscribers)
        for cb in subscribers:
            try:
                cb(event)
            except Exception:
                pass  # Silently ignore handler errors to not break other handlers
