from dataclasses import dataclass

@dataclass
class ReIDCustomConfig:
    """
    Настройки глобальной Re-ID галереи (ID Stitcher).

    Галерея решает ключевую проблему трекеров в ритейле:
    человек на несколько секунд ушёл за прилавок → трекер выдал ему новый ID.
    Галерея «склеивает» старый и новый ID, сохраняя непрерывность аналитики.

    Как работает:
      1. Накапливает усреднённые эмбеддинги для каждого активного трека.
      2. При «смерти» трека → сохраняет слепок в dead_pool.
      3. При появлении нового ID → сравнивает с dead_pool по косинусному сходству.
      4. При совпадении → подменяет ID через alias_map (без изменения трекера).
    """

    # ──────────────────────────────
    # Главный переключатель
    # ──────────────────────────────

    # [ON/OFF] Включить глобальную Re-ID галерею
    enabled: bool = False

    # ──────────────────────────────
    # Параметры совпадения
    # ──────────────────────────────

    # Порог косинусного сходства для склейки ID [0.0 – 1.0]
    # ↑ выше = строже (меньше ложных совпадений, но можно пропустить реальные)
    # Рекомендовано: 0.80–0.90 для ритейла с похожей одеждой персонала
    similarity_threshold: float = 0.65

    # Вес пространственного штрафа [0.0 – 1.0]
    # 0.0 = пространство не учитывается (чисто по эмбеддингу)
    # 0.3 = умеренный штраф за «телепортацию» — рекомендуется
    spatial_iou_weight: float = 0.3

    # ──────────────────────────────
    # Параметры памяти галереи
    # ──────────────────────────────

    # Как долго хранить «мёртвый» ID в галерее (в секундах)
    # После этого времени запись удаляется. 60с = 1 минута.
    max_age_seconds: float = 60.0

    # Максимальный размер dead_pool (при переполнении удаляется самый старый)
    max_gallery_size: int = 200

    # ──────────────────────────────
    # Multi-Shot (усреднение эмбеддингов)
    # ──────────────────────────────

    # Сколько кадров учитывает скользящее среднее эмбеддинга
    # Больше → стабильнее «портрет», но медленнее адаптация
    # Рекомендовано: 8–15 кадров
    embedding_history: int = 10

    # Минимальный confidence детекции для записи эмбеддинга в галерею
    # Грязные детекции (низкий conf) ухудшают «портрет» — фильтруем их
    min_conf_for_gallery: float = 0.45

    def __post_init__(self):
        if not (0.0 <= self.similarity_threshold <= 1.0):
            raise ValueError(f"similarity_threshold must be in [0.0, 1.0], got {self.similarity_threshold}")
        if not (0.0 <= self.spatial_iou_weight <= 1.0):
            raise ValueError(f"spatial_iou_weight must be in [0.0, 1.0], got {self.spatial_iou_weight}")
        if self.max_age_seconds <= 0:
            raise ValueError(f"max_age_seconds must be > 0, got {self.max_age_seconds}")
        if self.max_gallery_size < 1:
            raise ValueError(f"max_gallery_size must be >= 1, got {self.max_gallery_size}")
        if self.embedding_history < 1:
            raise ValueError(f"embedding_history must be >= 1, got {self.embedding_history}")
        if not (0.0 <= self.min_conf_for_gallery <= 1.0):
            raise ValueError(f"min_conf_for_gallery must be in [0.0, 1.0], got {self.min_conf_for_gallery}")
