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
