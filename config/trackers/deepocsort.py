from dataclasses import dataclass


@dataclass
class DeepOcSortConfig:
    """
    Конфигурация DeepOCSort трекера.
    Комбинирует устойчивость OC-SORT к прерываниям траектории с визуальным Re-ID.
    """

    # --- Основные пороги (добавлены для полноты управления) ---
    track_thresh: float = 0.4  # Порог детекции для начала трекинга
    max_age: int = 300  # Макс. количество кадров пропуска до удаления ID
    min_hits: int = 3  # Кадров для подтверждения нового объекта
    iou_threshold: float = 0.3  # Порог IoU для ассоциации

    # --- Специфичные параметры DeepOCSort ---
    delta_t: int = 3  # Временной шаг для вычисления скорости объекта
    inertia: float = 0.2  # Коэффициент инерции (вес предыдущего направления движения)

    # --- Настройка визуальных признаков (Embedding) ---
    w_association_emb: float = 0.5  # Вес эмбеддингов при сопоставлении (баланс между внешностью и геометрией)
    alpha_fixed_emb: float = 0.95  # Коэффициент обновления эмбеддинга (насколько сильно верим новому кадру)
    embedding_off: bool = False  # Отключение Re-ID (если True, превращается в обычный OCSort)

    # --- Адаптивное взвешивание (Appearance Weighting) ---
    aw_param: float = 0.5  # Параметр влияния внешности при расчете дистанции
    aw_off: bool = False  # Отключить адаптивное взвешивание внешности

    # --- Настройки фильтра Калмана (Scaling) ---
    # Влияют на то, насколько трекер "доверяет" предсказанию позиции и размера
    Q_xy_scaling: float = 0.1  # Масштабирование шума процесса для координат (x, y)
    Q_s_scaling: float = 0.01  # Масштабирование шума процесса для размера (scale)

    # --- Компенсация движения камеры ---
    cmc_off: bool = False  # Отключить компенсацию движения камеры (Camera Motion Compensation)

    def __post_init__(self):
        if not (0.0 <= self.track_thresh <= 1.0):
            raise ValueError(f"track_thresh must be in [0.0, 1.0], got {self.track_thresh}")
        if self.max_age < 1:
            raise ValueError(f"max_age must be >= 1, got {self.max_age}")
        if self.min_hits < 1:
            raise ValueError(f"min_hits must be >= 1, got {self.min_hits}")
        if not (0.0 <= self.iou_threshold <= 1.0):
            raise ValueError(f"iou_threshold must be in [0.0, 1.0], got {self.iou_threshold}")
        if self.delta_t < 1:
            raise ValueError(f"delta_t must be >= 1, got {self.delta_t}")
        if not (0.0 <= self.inertia <= 1.0):
            raise ValueError(f"inertia must be in [0.0, 1.0], got {self.inertia}")
        if not (0.0 <= self.w_association_emb <= 1.0):
            raise ValueError(f"w_association_emb must be in [0.0, 1.0], got {self.w_association_emb}")
        if not (0.0 <= self.alpha_fixed_emb <= 1.0):
            raise ValueError(f"alpha_fixed_emb must be in [0.0, 1.0], got {self.alpha_fixed_emb}")
        if not (0.0 <= self.aw_param <= 1.0):
            raise ValueError(f"aw_param must be in [0.0, 1.0], got {self.aw_param}")
        if self.Q_xy_scaling <= 0:
            raise ValueError(f"Q_xy_scaling must be > 0, got {self.Q_xy_scaling}")
        if self.Q_s_scaling <= 0:
            raise ValueError(f"Q_s_scaling must be > 0, got {self.Q_s_scaling}")
    
