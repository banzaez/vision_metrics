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
    # Размер пакета кадров для YOLO (batch size).
    # При 1 - минимальная задержка, при > 1 - выше пропускная способность.
    batch_size: int = 1
    # Фреймрейт исходного видео (кадров в секунду)
    frame_rate: int = 25
    # Пропуск кадров для ускорения: обрабатывается только каждый N-й кадр.
    # Эффективный FPS для трекера будет: frame_rate / (frame_skip + 1)
    frame_skip: int = 1
    # Количество потоков OpenCV для декодирования и обработки (оптимально: 4-8)
    opencv_threads: int = 4

@dataclass
class UIConfig:
    """Настройки пользовательского интерфейса и управления."""
    # Количество кадров для прыжка при нажатии вперед/назад в видеоплеере
    step_frames: int = 125
    # Флаг отображения мониторинга ресурсов (FPS, CPU, GPU, RAM)
    show_monitoring: bool = True

@dataclass
class SystemConfig:
    """Общая конфигурация системы."""
    perf: PerformanceConfig = field(default_factory=PerformanceConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Список источников видео (пути к файлам или ссылки на стримы)
    video_sources: List[str] = field(default_factory=lambda: [
        './data/videos/Camera_01_10.12.0.35_10.12.0.235_20260401113050_20260401113550_3084159.mp4'
    ])
