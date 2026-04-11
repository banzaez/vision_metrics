from .app_config import settings, AppConfig
from .registry import registry, ConfigRegistry

registry.register(settings)

__all__ = ['settings', 'AppConfig', 'registry', 'ConfigRegistry']
