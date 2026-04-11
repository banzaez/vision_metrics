from typing import Callable, Any
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ConfigChangeEvent:
    section: str
    key: str
    old_value: Any
    new_value: Any


class ConfigBus:
    _subscribers: list[Callable[[ConfigChangeEvent], None]] = []
    _lock: Lock = Lock()

    @classmethod
    def subscribe(cls, callback: Callable[[ConfigChangeEvent], None]) -> None:
        with cls._lock:
            cls._subscribers.append(callback)

    @classmethod
    def unsubscribe(cls, callback: Callable[[ConfigChangeEvent], None]) -> None:
        with cls._lock:
            cls._subscribers.remove(callback)

    @classmethod
    def notify(cls, event: ConfigChangeEvent) -> None:
        with cls._lock:
            subscribers = list(cls._subscribers)
        for cb in subscribers:
            try:
                cb(event)
            except Exception:
                pass
