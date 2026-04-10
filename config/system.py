import torch
from dataclasses import dataclass, field
from typing import List

def get_optimal_device() -> str:
    """Определяет наиболее подходящее вычислительное устройство."""
    if torch.cuda.is_available():
        return 'cuda'
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return 'mps'
    else:
        return 'cpu'

@dataclass
class PerformanceConfig:
    """Настройки производительности и вычислительного устройства."""

    # Устройство вычислений ('cpu', 'cuda', 'mps' для Mac)
    device: str = field(default_factory=get_optimal_device)

    # FP16 режим (рекомендуется для Mac M1)
    half: bool = False

    # Размер пакета кадров для YOLO (batch size).
    # При 1 - минимальная задержка, при > 1 - выше пропускная способность.
    batch_size: int = 1

    # Фреймрейт исходного видео (кадров в секунду)
    frame_rate: int = 25

    # Интервал обработки кадров: обрабатывать каждый N-й кадр для ускорения.
    # Эффективный FPS для трекера будет: frame_rate / frame_interval
    frame_interval: int = 3

    # Количество потоков OpenCV для декодирования и обработки (оптимально: 4-8)
    opencv_threads: int = 4

    def __post_init__(self):
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        if self.frame_rate <= 0:
            raise ValueError(f"frame_rate must be > 0, got {self.frame_rate}")
        if self.frame_interval < 1:
            raise ValueError(f"frame_interval must be >= 1, got {self.frame_interval}")
        if self.opencv_threads < 1:
            raise ValueError(f"opencv_threads must be >= 1, got {self.opencv_threads}")

@dataclass
class UIConfig:
    """Настройки пользовательского интерфейса и управления."""
    # Количество кадров для прыжка при нажатии вперед/назад в видеоплеере
    step_frames: int = 125
    # Флаг отображения мониторинга ресурсов (FPS, CPU, GPU, RAM)
    show_monitoring: bool = True

    def __post_init__(self):
        if self.step_frames < 1:
            raise ValueError(f"step_frames must be >= 1, got {self.step_frames}")

@dataclass
class SystemConfig:
    """Общая конфигурация системы."""
    perf: PerformanceConfig = field(default_factory=PerformanceConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Список источников видео (пути к файлам или ссылки на стримы)
    video_sources: List[str] = field(default_factory=lambda: [
        './data/videos/Camera_01_10.12.0.35_10.12.0.235_20260401113050_20260401113550_3084159.mp4'
    ])
