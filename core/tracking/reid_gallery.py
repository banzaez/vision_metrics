"""
ReID Gallery — глобальная галерея признаков для устранения смены ID.

Логика:
  1. Пока трек жив → накапливаем Multi-Shot историю эмбеддингов (скользящее среднее).
  2. Когда трекер «убивает» ID — перекладываем усреднённый эмбеддинг в dead_pool.
  3. При создании нового ID — ищем совпадение в dead_pool по косинусному сходству.
  4. При совпадении — добавляем запись в alias_map {new_id: old_id}.

Включается/выключается через TrackerConfig.gallery.enabled в config/tracker.py.
"""

import time
import logging

import numpy as np

logger = logging.getLogger(__name__)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Косинусное сходство между двумя векторами."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _bbox_center(bbox) -> tuple[float, float]:
    """Центр бокса (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def _spatial_penalty(bbox_old, bbox_new) -> float:
    """
    Пространственный штраф [0..1].
    0.0 = боксы совпадают (максимально близко).
    1.0 = очень далеко от друг друга.

    Используется как мягкий штраф, а не жёсткий фильтр.
    """
    cx_old, cy_old = _bbox_center(bbox_old)
    cx_new, cy_new = _bbox_center(bbox_new)

    # Средний размер человека как нормализатор (diagonal)
    w_old = abs(bbox_old[2] - bbox_old[0])
    h_old = abs(bbox_old[3] - bbox_old[1])
    diag = (w_old ** 2 + h_old ** 2) ** 0.5
    if diag < 1.0:
        return 1.0

    dist = ((cx_new - cx_old) ** 2 + (cy_new - cy_old) ** 2) ** 0.5
    # Нормализуем на 3 диагонали: дальше — штраф растёт
    penalty = min(dist / (3.0 * diag), 1.0)
    return penalty


class ReIDGallery:
    """
    Глобальная галерея Re-ID признаков для «склейки» ID.

    Атрибуты:
        alias_map (dict): {new_id -> old_id} — публичный словарь-переводчик.
    """

    def __init__(self, cfg):
        """
        Args:
            cfg: ReIDCustomConfig — конфигурация из config/reid_custom.py.
        """
        self.cfg = cfg
        self.alias_map: dict[int, int] = {}

        # Активные треки: {track_id: np.ndarray} — скользящий усреднённый эмбеддинг
        self._live_embeddings: dict[int, np.ndarray] = {}

        # Пул «мёртвых» треков: {old_id: {"emb": ..., "bbox": ..., "ts": ...}}
        self._dead_pool: dict[int, dict] = {}

        # Обратный словарь: old_id → new_id (чтобы не плодить дубли)
        self._reversed_map: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def feed_active(
        self,
        track_id: int,
        embedding: np.ndarray,
        conf: float,
        bbox: tuple,
    ) -> None:
        """
        Обновление живого трека новым эмбеддингом.
        Вызывать каждый кадр для каждого активного трека.

        Args:
            track_id: ID трека от BoxMOT.
            embedding: numpy-вектор признаков (shape [D]).
            conf: уверенность детекции.
            bbox: (x1, y1, x2, y2) — последний бокс в пикселях.
        """
        if embedding is None or embedding.size == 0:
            return

        # Фильтр качества — не берём грязные детекции
        if conf < self.cfg.min_conf_for_gallery:
            return

        emb = embedding.flatten().astype(np.float64)

        if track_id not in self._live_embeddings:
            self._live_embeddings[track_id] = emb
        else:
            # Экспоненциальное скользящее среднее (как в BoxMOT)
            alpha = 1.0 / self.cfg.embedding_history
            self._live_embeddings[track_id] = (
                (1.0 - alpha) * self._live_embeddings[track_id] + alpha * emb
            )

    def on_track_lost(self, track_id: int, bbox: tuple) -> None:
        """
        Перенести трек из живых в dead_pool.
        Вызывать когда BoxMOT удалил старый ID.

        Args:
            track_id: удалённый ID.
            bbox: последний известный бокс (x1, y1, x2, y2).
        """
        if track_id not in self._live_embeddings:
            logger.debug(f"[ReIDGallery] on_track_lost: нет эмбеддинга для id={track_id}")
            return

        # Обрезаем галерею если она переполнена
        while len(self._dead_pool) >= self.cfg.max_gallery_size:
            oldest = min(self._dead_pool, key=lambda k: self._dead_pool[k]["ts"])
            del self._dead_pool[oldest]
            self._reversed_map.pop(oldest, None)

        self._dead_pool[track_id] = {
            "emb": self._live_embeddings.pop(track_id),
            "bbox": bbox,
            "ts": time.time(),
        }
        logger.debug(f"[ReIDGallery] Перемещён в dead_pool: id={track_id}")

    def match_new_track(
        self,
        new_id: int,
        embedding: np.ndarray,
        bbox: tuple,
    ) -> int | None:
        """
        Поиск совпадения нового трека среди «мёртвых» ID.

        Args:
            new_id: свежесозданный ID трекера.
            embedding: эмбеддинг нового трека.
            bbox: бокс нового трека.

        Returns:
            old_id если найдено совпадение, иначе None.
        """
        if embedding is None or embedding.size == 0 or not self._dead_pool:
            return None

        emb = embedding.flatten().astype(np.float64)
        best_id = None
        best_score = -1.0

        for old_id, data in self._dead_pool.items():
            # Уже "занятый" мёртвый ID пропускаем
            if old_id in self._reversed_map:
                continue

            cos_sim = _cosine_similarity(emb, data["emb"])
            if cos_sim < self.cfg.similarity_threshold:
                continue

            # Пространственный штраф
            if self.cfg.spatial_iou_weight > 0.0:
                penalty = _spatial_penalty(data["bbox"], bbox)
                score = cos_sim * (1.0 - self.cfg.spatial_iou_weight * penalty)
            else:
                score = cos_sim

            if score > best_score:
                best_score = score
                best_id = old_id

        if best_id is not None:
            self._reversed_map[best_id] = new_id
            logger.info(
                f"[ReIDGallery] Склейка: new_id={new_id} → old_id={best_id} "
                f"(cosine={_cosine_similarity(emb, self._dead_pool[best_id]['emb']):.3f})"
            )

        return best_id

    def apply_alias(self, track_id: int) -> int:
        """
        Применить alias_map к track_id.
        Рекурсивно раскрывает цепочки алиасов.

        Args:
            track_id: входной ID.

        Returns:
            Канонический (старейший) ID.
        """
        visited = set()
        current = track_id
        while current in self.alias_map and current not in visited:
            visited.add(current)
            current = self.alias_map[current]
        return current

    def cleanup(self) -> None:
        """Удалить устаревшие записи из dead_pool."""
        now = time.time()
        expired = [
            tid for tid, data in self._dead_pool.items()
            if (now - data["ts"]) > self.cfg.max_age_seconds
        ]
        for tid in expired:
            del self._dead_pool[tid]
            self._reversed_map.pop(tid, None)
        if expired:
            logger.debug(f"[ReIDGallery] Очистка: удалено {len(expired)} устаревших записей")

    def extract_embeddings_from_tracker(self, tracker) -> dict[int, np.ndarray]:
        """
        Извлечение текущих эмбеддингов из внутренних структур BoxMOT-трекера.
        Поддерживает трекеры с атрибутом active_tracks (HybridSort, BoTSORT, DeepOCSort и др.)

        Args:
            tracker: экземпляр BoxMOT-трекера.

        Returns:
            Словарь {track_id: embedding_vector}.
        """
        result = {}

        # Большинство трекеров используют self.active_tracks (список объектов с .id и .smooth_feat)
        if hasattr(tracker, "active_tracks"):
            for trk in tracker.active_tracks:
                tid = getattr(trk, "id", None)
                feat = getattr(trk, "smooth_feat", None)
                if tid is not None and feat is not None:
                    result[tid] = np.array(feat, dtype=np.float64)

        # BotSort / StrongSort используют self.tracked_stracks
        elif hasattr(tracker, "tracked_stracks"):
            for trk in tracker.tracked_stracks:
                tid = getattr(trk, "track_id", None)
                feat = getattr(trk, "smooth_feat", None)
                if tid is not None and feat is not None:
                    result[tid] = np.array(feat, dtype=np.float64)

        return result
