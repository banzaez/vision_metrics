from dataclasses import dataclass
from config.system import PerformanceConfig

perf = PerformanceConfig()

@dataclass
class ByteTrackConfig:
    """Конфигурация ByteTrack трекера."""
    # Вычислительные ресурсы
    device: str = None                # Устройство (если None, берется из system.py)

    # Пороги уверенности и ассоциации
    track_thresh: float = 0.4         # Порог для первичной ассоциации (надежной)
    match_thresh: float = 0.8         # Порог IoU для ассоциации
    
    # Параметры памяти и ассоциации
    track_buffer: int = 31           # Буфер памяти трека в кадрах

    # FPS привязан к системному frame_skip: чем больше пропуск, тем меньше эффективный FPS
    frame_rate: int = perf.frame_rate // (perf.frame_skip + 1)
    
    # Режим детекций
    per_class: bool = False           # Независимый трекинг для каждого класса
