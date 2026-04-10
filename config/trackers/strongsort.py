from dataclasses import dataclass


@dataclass
class StrongSortConfig:
    """
    Конфигурация StrongSort трекера.
    Улучшенная версия DeepSORT с акцентом на визуальную стабильность.
    """

    # --- Пороги уверенности ---
    min_conf: float = 0.1  # Минимальный порог уверенности для учета объекта

    # --- Дистанции и ассоциация ---
    # Порог косинусного расстояния: чем меньше, тем строже проверка внешности
    max_cos_dist: float = 0.2  # Макс. визуальное различие для объединения треков
    # Порог IoU: 0.7 означает, что нужно 30% пересечения рамок для ассоциации
    max_iou_dist: float = 0.9  # Макс. геометрическая дистанция (1 - IoU)

    # --- Жизненный цикл трека ---
    n_init: int = 5  # Количество кадров для подтверждения нового ID
    max_age: int = 240  # Сколько кадров "помнить" объект после исчезновения

    # --- Память и фильтрация ---
    nn_budget: int = 100  # Лимит хранимых признаков (эмбеддингов) для каждого ID

    # --- Веса и сглаживание ---
    # Баланс между движением и внешностью (Motion-Appearance Lambda)
    mc_lambda: float = 0.5  # Больше 0.5 — приоритет отдается внешности (Re-ID)

    # Экспоненциальное скользящее среднее (EMA) для обновления признаков объекта
    ema_alpha: float = 0.7  # Скорость обновления "памяти" внешности (0.9 — очень быстро)

    def __post_init__(self):
        if not (0.0 <= self.min_conf <= 1.0):
            raise ValueError(f"min_conf must be in [0.0, 1.0], got {self.min_conf}")
        if not (0.0 <= self.max_cos_dist <= 1.0):
            raise ValueError(f"max_cos_dist must be in [0.0, 1.0], got {self.max_cos_dist}")
        if not (0.0 <= self.max_iou_dist <= 1.0):
            raise ValueError(f"max_iou_dist must be in [0.0, 1.0], got {self.max_iou_dist}")
        if self.n_init < 1:
            raise ValueError(f"n_init must be >= 1, got {self.n_init}")
        if self.max_age < 1:
            raise ValueError(f"max_age must be >= 1, got {self.max_age}")
        if self.nn_budget < 1:
            raise ValueError(f"nn_budget must be >= 1, got {self.nn_budget}")
        if not (0.0 <= self.mc_lambda <= 1.0):
            raise ValueError(f"mc_lambda must be in [0.0, 1.0], got {self.mc_lambda}")
        if not (0.0 < self.ema_alpha < 1.0):
            raise ValueError(f"ema_alpha must be in (0.0, 1.0), got {self.ema_alpha}")
