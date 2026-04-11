"""Backward compatibility: re-export from sections.tracker."""

from config.sections.tracker import (
    TrackerType,
    ReIDModel,
    TrackerConfigEntry,
    TrackerRegistry,
    TrackerConfig,
)

__all__ = [
    "TrackerType",
    "ReIDModel",
    "TrackerConfigEntry",
    "TrackerRegistry",
    "TrackerConfig",
]
