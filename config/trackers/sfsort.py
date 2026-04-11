from dataclasses import dataclass
from typing import Optional


@dataclass
class SFSortConfig:
    """
    Конфигурация SF-SORT трекера.
    Ориентирован на высокую скорость работы с использованием простых визуальных признаков.
    """
    # --- Основные пороги уверенности (Thresholds) ---
    high_th: Optional[float] = 0.6            # Порог для надежных детекций (первый этап)
    match_th_first: Optional[float] = 0.67    # Порог IoU для первого этапа ассоциации
    new_track_th: Optional[float] = 0.7       # Порог уверенности для создания нового ID
    low_th: Optional[float] = 0.1             # Минимальный порог для учета объекта (второй этап)
    match_th_second: Optional[float] = 0.3    # Порог IoU для ассоциации "слабых" детекций
    
    # --- Динамическая настройка и классификация ---
    dynamic_tuning: bool = False              # Включить динамическую подстройку порогов
    cth: Optional[float] = 0.5                # Порог классификации (Confidence Threshold)
    
    # --- Параметры модификации (М-параметры) ---
    # Позволяют смещать базовые пороги в зависимости от условий кадра
    high_th_m: Optional[float] = 0            # Модификатор высокого порога
    new_track_th_m: Optional[float] = 0       # Модификатор порога нового трека
    match_th_first_m: Optional[float] = 0     # Модификатор первого этапа ассоциации
    
    # --- Геометрия и OBB (Oriented Bounding Boxes) ---
    obb_theta_damping: float = 0.8            # Коэффициент затухания угла поворота рамки
    
    # --- Тайм-ауты зон (Зональная память) ---
    marginal_timeout: Optional[int] = 0       # Время ожидания объекта в краевых зонах кадра
    central_timeout: Optional[int] = 0        # Время ожидания объекта в центральной зоне кадра
    
    # --- Размеры кадра и настройки полей (Margins) ---
    # Необходимы для работы зональных тайм-аутов и логики появления/исчезновения
    frame_width: Optional[int] = None         # Ширина кадра
    frame_height: Optional[int] = None        # Высота кадра
    horizontal_margin: Optional[int] = None   # Размер горизонтальных полей от края
    vertical_margin: Optional[int] = None     # Размер вертикальных полей от края
