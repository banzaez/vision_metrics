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

    def __post_init__(self):
        def validate_01(val, name):
            if val is not None and not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be in [0.0, 1.0], got {val}")

        validate_01(self.high_th, "high_th")
        validate_01(self.match_th_first, "match_th_first")
        validate_01(self.new_track_th, "new_track_th")
        validate_01(self.low_th, "low_th")
        validate_01(self.match_th_second, "match_th_second")
        validate_01(self.cth, "cth")
        
        if not (0.0 <= self.obb_theta_damping <= 1.0):
            raise ValueError(f"obb_theta_damping must be in [0.0, 1.0], got {self.obb_theta_damping}")
            
        if self.marginal_timeout is not None and self.marginal_timeout < 0:
            raise ValueError(f"marginal_timeout must be >= 0, got {self.marginal_timeout}")
        if self.central_timeout is not None and self.central_timeout < 0:
            raise ValueError(f"central_timeout must be >= 0, got {self.central_timeout}")
            
        if self.frame_width is not None and self.frame_width < 0:
            raise ValueError(f"frame_width must be >= 0, got {self.frame_width}")
        if self.frame_height is not None and self.frame_height < 0:
            raise ValueError(f"frame_height must be >= 0, got {self.frame_height}")
        if self.horizontal_margin is not None and self.horizontal_margin < 0:
            raise ValueError(f"horizontal_margin must be >= 0, got {self.horizontal_margin}")
        if self.vertical_margin is not None and self.vertical_margin < 0:
            raise ValueError(f"vertical_margin must be >= 0, got {self.vertical_margin}")