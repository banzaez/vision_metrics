from dataclasses import dataclass


@dataclass
class BotSortConfig:
    """Конфигурация BoTSORT трекера."""

    # --- Пороги уверенности детектора (YOLO) ---
    track_low_thresh: float = 0.1  # Минимум для учета детекции во вторую очередь
    track_high_thresh: float = 0.5  # Порог для первичной ассоциации
    new_track_thresh: float = 0.6  # Порог для создания нового трека

    # --- Параметры памяти и ассоциации ---
    track_buffer: int = 200  # Сколько кадров "помнить" объект
    match_thresh: float = 0.8  # Порог геометрического совпадения (IoU)
    proximity_thresh: float = 0.5  # Порог ограничения области поиска
    appearance_thresh: float = 0.6  # Порог визуального сходства (Re-ID)

    # --- Дополнительные флаги ---
    fuse_first_associate: bool = False  # Скрещивать ли IoU и Re-ID на первом шаге
    per_class: bool = False  # Независимый трекинг для каждого класс

    def __post_init__(self):
        if not (0.0 <= self.track_low_thresh <= 1.0):
            raise ValueError(f"track_low_thresh must be in [0.0, 1.0], got {self.track_low_thresh}")
        if not (0.0 <= self.track_high_thresh <= 1.0):
            raise ValueError(f"track_high_thresh must be in [0.0, 1.0], got {self.track_high_thresh}")
        if not (0.0 <= self.new_track_thresh <= 1.0):
            raise ValueError(f"new_track_thresh must be in [0.0, 1.0], got {self.new_track_thresh}")
        if self.track_buffer < 1:
            raise ValueError(f"track_buffer must be >= 1, got {self.track_buffer}")
        if not (0.0 <= self.match_thresh <= 1.0):
            raise ValueError(f"match_thresh must be in [0.0, 1.0], got {self.match_thresh}")
        if not (0.0 <= self.proximity_thresh <= 1.0):
            raise ValueError(f"proximity_thresh must be in [0.0, 1.0], got {self.proximity_thresh}")
        if not (0.0 <= self.appearance_thresh <= 1.0):
            raise ValueError(f"appearance_thresh must be in [0.0, 1.0], got {self.appearance_thresh}")
