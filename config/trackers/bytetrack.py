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

    def __post_init__(self):
        if not (0.0 <= self.det_thresh <= 1.0):
            raise ValueError(f"det_thresh must be in [0.0, 1.0], got {self.det_thresh}")
        if self.max_age < 1:
            raise ValueError(f"max_age must be >= 1, got {self.max_age}")
        if self.max_obs < 1:
            raise ValueError(f"max_obs must be >= 1, got {self.max_obs}")
        if self.min_hits < 1:
            raise ValueError(f"min_hits must be >= 1, got {self.min_hits}")
        if not (0.0 <= self.iou_threshold <= 1.0):
            raise ValueError(f"iou_threshold must be in [0.0, 1.0], got {self.iou_threshold}")
        if not (0.0 <= self.min_conf <= 1.0):
            raise ValueError(f"min_conf must be in [0.0, 1.0], got {self.min_conf}")
        if not (0.0 <= self.track_thresh <= 1.0):
            raise ValueError(f"track_thresh must be in [0.0, 1.0], got {self.track_thresh}")
        if not (0.0 <= self.match_thresh <= 1.0):
            raise ValueError(f"match_thresh must be in [0.0, 1.0], got {self.match_thresh}")
        if self.track_buffer < 1:
            raise ValueError(f"track_buffer must be >= 1, got {self.track_buffer}")
        if self.asso_func not in ["iou", "reid"]:
            raise ValueError(f"asso_func must be 'iou' or 'reid', got {self.asso_func}")
