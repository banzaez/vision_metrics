from dataclasses import dataclass


@dataclass
class ByteTrackConfig:
    """Конфигурация ByteTrack трекера."""

    # Пороги уверенности и ассоциации
    track_thresh: float = 0.4  # Порог для первичной ассоциации (надежной)
    match_thresh: float = 0.8  # Порог IoU для ассоциации

    # Параметры памяти и ассоциации
    track_buffer: int = 150  # Буфер памяти трека в кадрах

    # Режим детекций
    per_class: bool = False  # Независимый трекинг для каждого класса
