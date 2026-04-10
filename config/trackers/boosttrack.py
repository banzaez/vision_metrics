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
