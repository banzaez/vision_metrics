from dataclasses import dataclass


@dataclass
class ByteTrackConfig:
    """Конфигурация ByteTrack трекера."""

    # Пороги уверенности и ассоциации
    det_thresh: float = 0.3

    # Порог для первичной ассоциации (надежной)
    max_age: int = 150

    # Максимальное количество наблюдений для трека
    max_obs: int = 200

    # Минимальное количество наблюдений для трека
    min_hits: int = 3

    # Порог IoU для ассоциации
    iou_threshold: float = 0.3

    # Функция ассоциации
    asso_func: str = "iou"  # iou или reid
    min_conf: float = 0.1  # Минимальный confidence детекции для записи эмбеддинга в галерею
    track_thresh: float = 0.4  # Порог для первичной ассоциации (надежной)
    match_thresh: float = 0.8  # Порог IoU для ассоциации
    track_buffer: int = 150  # Буфер памяти трека в кадрах
    with_reid: bool = True  # Использовать ReID для ассоциации

    # Режим детекций
    per_class: bool = False  # Независимый трекинг для каждого класса
