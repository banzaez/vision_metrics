from dataclasses import dataclass


@dataclass
class HybridSortConfig:
    """
    Конфигурация HybridSort трекера.
    Оптимизирована для ритейла: долгое удержание ID и высокий приоритет Re-ID признаков.
    """

    # --- Логика BYTE (работа с низким конфиденсом) ---
    use_byte: bool = True                # Использовать логику ByteTrack для слабых детекций
    track_thresh: float = 0.3            # Порог для надежных детекций
    low_thresh: float = 0.1              # Порог для "подозрительных" детекций

    # --- Параметры движения и инерции ---
    delta_t: int = 3                     # Шаг времени для расчета вектора скорости
    inertia: float = 0.2                 # Усиленная инерция для стабильности при резких поворотах
    use_custom_kf: bool = True           # Использовать расширенный фильтр Калмана
    
    # --- Базовые параметры удержания ---
    det_thresh: float = 0.3              # Порог уверенности для детекции
    max_age: int = 150                   # Помним объект ~18-20 секунд при низком FPS
    max_obs: int = 200                   # Буфер наблюдений (должен быть >= max_age для стабильности)
    min_hits: int = 3                    # Кадров для инициации подтвержденного трека
    iou_threshold: float = 0.3           # Порог IoU для базовой ассоциации
    per_class: bool = False              # Глобальный трекинг без деления на классы
    asso_func: str = 'diou'              # Distance-IoU: лучше учитывает близость центров объектов

    # --- Долгосрочная память (Long-term Re-ID) ---
    with_longterm_reid: bool = True      # Хранение истории визуальных признаков
    longterm_bank_length: int = 120      # Глубина истории признаков для усреднения
    longterm_reid_weight: float = 0.7    # Увеличенное влияние внешности на принятие решения
    
    # --- Интеллектуальная коррекция ---
    with_longterm_reid_correction: bool = True      # Исправление ID при высокой уверенности Re-ID
    longterm_reid_correction_thresh: float = 0.3    # Порог для "возрождения" старых ID
    longterm_reid_correction_thresh_low: float = 0.35 

    # --- Баланс Геометрии и Внешности (EG Weights) ---
    # Позволяет игнорировать странные перемещения, если человек визуально опознан
    EG_weight_high_score: float = 5.0    # Высокий приоритет Re-ID при хорошей видимости
    EG_weight_low_score: float = 2.0     # Приоритет геометрии при плохой видимости (блюр, спина)

    # --- TCM (Trajectory Continuity Module) ---

    # --- Пороги и настройки ---
    high_score_matching_thresh: float = 0.45  # Порог IoU для надежных объектов
    alpha: float = 0.8                   # Коэффициент сглаживания при обновлении признаков
    adapfs: bool = False                 # Адаптивный выбор признаков (Adaptive Feature Selection)
    cmc_method: str = 'sof'              # Метод компенсации движения камеры (sof быстрее чем ecc)
    dataset: str = 'custom'              # Имя набора данных (для внутренней оптимизации)

    def __post_init__(self):
        if not (0.0 <= self.track_thresh <= 1.0):
            raise ValueError(f"track_thresh must be in [0.0, 1.0], got {self.track_thresh}")
        if not (0.0 <= self.low_thresh <= 1.0):
            raise ValueError(f"low_thresh must be in [0.0, 1.0], got {self.low_thresh}")
        if self.delta_t < 1:
            raise ValueError(f"delta_t must be >= 1, got {self.delta_t}")
        if not (0.0 <= self.inertia <= 1.0):
            raise ValueError(f"inertia must be in [0.0, 1.0], got {self.inertia}")
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
        if self.longterm_bank_length < 1:
            raise ValueError(f"longterm_bank_length must be >= 1, got {self.longterm_bank_length}")
        if not (0.0 <= self.longterm_reid_weight <= 1.0):
            raise ValueError(f"longterm_reid_weight must be in [0.0, 1.0], got {self.longterm_reid_weight}")
        if not (0.0 <= self.longterm_reid_correction_thresh <= 1.0):
            raise ValueError(f"longterm_reid_correction_thresh must be in [0.0, 1.0], got {self.longterm_reid_correction_thresh}")
        if not (0.0 <= self.longterm_reid_correction_thresh_low <= 1.0):
            raise ValueError(f"longterm_reid_correction_thresh_low must be in [0.0, 1.0], got {self.longterm_reid_correction_thresh_low}")
        if self.EG_weight_high_score < 0:
            raise ValueError(f"EG_weight_high_score must be >= 0, got {self.EG_weight_high_score}")
        if self.EG_weight_low_score < 0:
            raise ValueError(f"EG_weight_low_score must be >= 0, got {self.EG_weight_low_score}")
        if not (0.0 <= self.high_score_matching_thresh <= 1.0):
            raise ValueError(f"high_score_matching_thresh must be in [0.0, 1.0], got {self.high_score_matching_thresh}")
        if not (0.0 < self.alpha < 1.0):
            raise ValueError(f"alpha must be in (0.0, 1.0), got {self.alpha}")
