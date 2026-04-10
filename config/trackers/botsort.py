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
