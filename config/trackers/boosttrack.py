from dataclasses import dataclass


@dataclass
class BoostTrackConfig:
    """
    Конфигурация BoostTrack трекера.
    Самый точный трекер в BoxMOT, использующий 'бустинг' детекций.
    """

    # --- Базовые пороги (как в ByteTrack) ---
    track_thresh: float = 0.4  # Порог первой ассоциации
    min_conf: float = 0.1  # Минимальный порог для учета объекта
    match_thresh: float = 0.3  # Порог IoU для сопоставления
    track_buffer: int = 120  # Сколько кадров помнить объект (max_age)

    # --- Специфичные параметры BoostTrack ---
    use_ecc: bool = False  # Компенсация движения камеры (убирает "тряску" ID)
    cmc_method: str = "disabled"  # Метод компенсации (ecc, orb, sift)
    min_box_area: int = 10  # Игнорировать слишком маленькие объекты (шум)
    aspect_ratio_thresh: float = 2.0  # Макс. соотношение сторон (фильтр аномальных рамок)

    # --- Веса ассоциации (Lambdas) ---
    # Эти три параметра в сумме должны давать 1.0
    lambda_iou: float = 0.3  # Вес геометрического совпадения (IoU)
    lambda_mhd: float = 0.5  # Вес расстояния Махаланобиса (динамика движения)
    lambda_shape: float = 0.2  # Вес изменения формы рамки

    # --- Бустинг (главная фишка) ---
    use_dlo_boost: bool = True  # Использовать Deep Learning Objects boost
    use_duo_boost: bool = True  # Использовать Detection Uncertainty Optimization
    dlo_boost_coef: float = 0.8  # Насколько сильно доверять "улучшенным" рамкам

    # --- Продвинутые фильтры (обычно False) ---
    s_sim_corr: bool = False  # Коррекция сходства формы
    use_rich_s: bool = False  # Использовать "богатые" признаки формы
    use_sb: bool = False  # Structural Break detection
    use_vt: bool = False  # Visual Tracking (доп. зрение)

    def __post_init__(self):
        if not (0.0 <= self.track_thresh <= 1.0):
            raise ValueError(f"track_thresh must be in [0.0, 1.0], got {self.track_thresh}")
        if not (0.0 <= self.min_conf <= 1.0):
            raise ValueError(f"min_conf must be in [0.0, 1.0], got {self.min_conf}")
        if not (0.0 <= self.match_thresh <= 1.0):
            raise ValueError(f"match_thresh must be in [0.0, 1.0], got {self.match_thresh}")
        if self.track_buffer < 1:
            raise ValueError(f"track_buffer must be >= 1, got {self.track_buffer}")
        if self.min_box_area < 1:
            raise ValueError(f"min_box_area must be >= 1, got {self.min_box_area}")
        if self.aspect_ratio_thresh <= 0:
            raise ValueError(f"aspect_ratio_thresh must be > 0, got {self.aspect_ratio_thresh}")
        if not (0.0 <= self.lambda_iou <= 1.0):
            raise ValueError(f"lambda_iou must be in [0.0, 1.0], got {self.lambda_iou}")
        if not (0.0 <= self.lambda_mhd <= 1.0):
            raise ValueError(f"lambda_mhd must be in [0.0, 1.0], got {self.lambda_mhd}")
        if not (0.0 <= self.lambda_shape <= 1.0):
            raise ValueError(f"lambda_shape must be in [0.0, 1.0], got {self.lambda_shape}")
        if not (0.0 <= self.dlo_boost_coef <= 1.0):
            raise ValueError(f"dlo_boost_coef must be in [0.0, 1.0], got {self.dlo_boost_coef}")
