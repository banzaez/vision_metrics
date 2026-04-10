from dataclasses import dataclass


@dataclass
class OcSortConfig:
    """
    Конфигурация OCSort трекера.
    Фокусируется на сглаживании траекторий и уменьшении ошибок фильтра Калмана.
    """

    # --- Специфичные параметры OC-SORT ---
    delta_t: int = 3  # Временной промежуток для оценки вектора скорости
    inertia: float = 0.2  # Коэффициент инерции (сопротивление резкой смене направления)

    # --- Режимы работы ---
    use_byte: bool = False  # Использовать ли логику BYTE для низких скоров (обычно в OC-SORT выключено)

    # --- Настройка фильтра Калмана (Масштабирование шума) ---
    # Позволяют настроить "гибкость" предсказания под динамику в магазине
    Q_xy_scaling: float = 0.01  # Шум процесса для позиции (x, y). Выше — трекер быстрее адаптируется к рывкам.
    Q_s_scaling: float = 0.0001  # Шум процесса для масштаба (размера). Выше — позволяет объекту быстрее "расти" в кадре.

    def __post_init__(self):
        if self.delta_t < 1:
            raise ValueError(f"delta_t must be >= 1, got {self.delta_t}")
        if not (0.0 <= self.inertia <= 1.0):
            raise ValueError(f"inertia must be in [0.0, 1.0], got {self.inertia}")
        if self.Q_xy_scaling <= 0:
            raise ValueError(f"Q_xy_scaling must be > 0, got {self.Q_xy_scaling}")
        if self.Q_s_scaling <= 0:
            raise ValueError(f"Q_s_scaling must be > 0, got {self.Q_s_scaling}")
