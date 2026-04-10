from dataclasses import dataclass


@dataclass
class HybridSortConfig:
    """
    Конфигурация HybridSort трекера.
    Использует адаптивные веса для разных уровней уверенности детекции (High/Low score).
    """

    # --- Логика BYTE (работа с низким конфиденсом) ---
    use_byte: bool = True                # Использовать логику ByteTrack для слабых детекций
    track_thresh: float = 0.3            # Порог для надежных детекций
    low_thresh: float = 0.1              # Порог для "подозрительных" детекций

    # --- Параметры движения и инерции ---
    delta_t: int = 3                     # Шаг времени для расчета вектора скорости
    inertia: float = 0.1                 # Сила инерции (сопротивление резкой смене вектора)
    use_custom_kf: bool = True           # Использовать кастомный фильтр Калмана
    
    # --- Базовые пороги детекции ---
    det_thresh: float = 0.3              # Порог уверенности для детекции
    max_age: int = 100                   # Сколько кадров "помнить" объект без детекции
    max_obs: int = 50                    # Макс. количество наблюдений (обычно <= max_age)
    min_hits: int = 3                    # Кадров для подтверждения нового объекта
    iou_threshold: float = 0.3           # Порог IoU для ассоциации
    per_class: bool = False              # Независимый трекинг для разных классов
    asso_func: str = 'iou'               # Функция ассоциации (iou, giou, diou, ciou)

    # --- Долгосрочная память (Long-term Re-ID) ---
    with_longterm_reid: bool = True      # Хранить "паспорт" объекта в памяти
    longterm_bank_length: int = 90       # Сколько последних эмбеддингов хранить в банке
    longterm_reid_weight: float = 0.6    # Вес долгосрочной памяти при ассоциации (увеличено с 0.3)
    
    # --- Коррекция по долгосрочной памяти ---
    with_longterm_reid_correction: bool = True      # Исправлять ID, если Re-ID банк уверен в совпадении
    longterm_reid_correction_thresh: float = 0.3    # Порог для коррекции надежных объектов
    longterm_reid_correction_thresh_low: float = 0.35 # Порог для коррекции слабых объектов

    # --- EG (Embedding-Geometry) веса ---
    # Определяют баланс между "внешностью" и "позицией" для разных типов детекций
    EG_weight_high_score: float = 4.6    # Вес для четких детекций (выше — больше верим Re-ID)
    EG_weight_low_score: float = 2.0     # Вес для размытых детекций (больше верим геометрии)

    # --- TCM (Trajectory Continuity Module) ---
    # Модуль непрерывности траектории (чтобы ID не "прыгали" на пустые места)
    TCM_first_step: bool = True          # Использовать TCM на первом этапе сопоставления
    TCM_byte_step: bool = True           # Использовать TCM для слабых детекций
    TCM_byte_step_weight: float = 1.0    # Влияние модуля на этапе BYTE

    # --- Пороги и настройки ---
    high_score_matching_thresh: float = 0.45  # Порог IoU для надежных объектов
    alpha: float = 0.8                   # Коэффициент сглаживания при обновлении признаков
    adapfs: bool = False                 # Адаптивный выбор признаков (Adaptive Feature Selection)
    cmc_method: str = 'sof'              # Метод компенсации движения камеры (sof быстрее чем ecc)
    dataset: str = 'custom'              # Имя набора данных (для внутренней оптимизации)
