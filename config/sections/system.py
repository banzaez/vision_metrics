import torch
from dataclasses import dataclass, field
from typing import List


def _get_optimal_device() -> str:
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

    device: str = field(default_factory=_get_optimal_device)
    """Устройство вычислений ('cpu', 'cuda', 'mps' для Mac)"""

    def __post_init__(self):
        if self.device == 'auto':
            self.device = _get_optimal_device()

    half: bool = True
    """FP16 режим (рекомендуется для Mac M1)"""

    batch_size: int = 1
    """Размер пакета кадров для YOLO. 1 = минимальная задержка, >1 = выше пропускная способность."""

    frame_rate: int = 25
    """Фреймрейт исходного видео. Используется как fallback, если метаданные недоступны."""

    frame_interval: int = 3
    """Обрабатывать каждый N-й кадр. Эффективный FPS = frame_rate / frame_interval."""

    opencv_threads: int = 4
    """Количество потоков OpenCV для декодирования и обработки (оптимально: 4-8)."""


@dataclass
class UIConfig:
    """Настройки пользовательского интерфейса."""

    step_frames: int = 125
    """Количество кадров для прыжка при нажатии вперед/назад в видеоплеере."""

    show_monitoring: bool = True
    """Флаг отображения мониторинга ресурсов (FPS, CPU, GPU, RAM)."""


@dataclass
class SystemConfig:
    """Общая конфигурация системы."""

    perf: PerformanceConfig = field(default_factory=PerformanceConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    video_sources: List[str] = field(default_factory=lambda: [
        './data/videos/Camera_01_10.12.0.35_10.12.0.235_20260401113050_20260401113550_3084159.mp4'
    ])
    """Список источников видео (пути к файлам или ссылки на стримы)."""
