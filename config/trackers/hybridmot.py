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
    max_age: int = 500                   # Сколько кадров "помнить" объект без детекции (90 = ~3.6 сек)

    # --- Долгосрочная память (Long-term Re-ID) ---
    with_longterm_reid: bool = True      # Хранить "паспорт" объекта в памяти
    longterm_bank_length: int = 90       # Сколько последних эмбеддингов хранить в банке
    longterm_reid_weight: float = 0.9    # Вес долгосрочной памяти при ассоциации (увеличено с 0.3)
    
    # --- Коррекция по долгосрочной памяти ---
    with_longterm_reid_correction: bool = True      # Исправлять ID, если Re-ID банк уверен в совпадении
    longterm_reid_correction_thresh: float = 0.3    # Порог для коррекции надежных объектов
    longterm_reid_correction_thresh_low: float = 0.1 # Порог для коррекции слабых объектов

    # --- EG (Embedding-Geometry) веса ---
    # Определяют баланс между "внешностью" и "позицией" для разных типов детекций
    EG_weight_high_score: float = 4.6    # Вес для четких детекций (выше — больше верим Re-ID)
    EG_weight_low_score: float = 1.3     # Вес для размытых детекций (больше верим геометрии)

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
