from dataclasses import dataclass


class ConfigRegistry:
    """
    Централизованный доступ к конфигурациям.
    Позволяет получать и изменять настройки через единый интерфейс.
    """
    _instance = None
    _settings = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, settings) -> None:
        self._settings = settings
    
    def get(self, config_name: str) -> dataclass:
        if self._settings is None:
            raise RuntimeError("ConfigRegistry not initialized. Call register(settings) first.")
        return getattr(self._settings, config_name, None)
    
    def set(self, config_name: str, **kwargs) -> None:
        if self._settings is None:
            raise RuntimeError("ConfigRegistry not initialized. Call register(settings) first.")
        cfg = getattr(self._settings, config_name, None)
        if cfg is None:
            raise ValueError(f"Config '{config_name}' not found")
        for k, v in kwargs.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
    
    def list_configs(self) -> list[str]:
        if self._settings is None:
            return []
        return [attr for attr in dir(self._settings) if not attr.startswith('_')]


registry = ConfigRegistry()