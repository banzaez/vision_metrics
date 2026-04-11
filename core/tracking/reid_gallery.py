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
import threading

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
    # Используем среднее между старым и новым боксом для стабильности
    def get_diag(b):
        return (abs(b[2] - b[0])**2 + abs(b[3] - b[1])**2)**0.5

    diag_old = get_diag(bbox_old)
    diag_new = get_diag(bbox_new)
    avg_diag = (diag_old + diag_new) / 2.0

    if avg_diag < 1.0:
        return 1.0

    dist = ((cx_new - cx_old) ** 2 + (cy_new - cy_old) ** 2) ** 0.5
    # Нормализуем на 3 диагонали: дальше — штраф растёт
    penalty = min(dist / (3.0 * avg_diag), 1.0)
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
        self.lock = threading.RLock()
        self.alias_map: dict[int, int] = {}
        self.stitch_scores: dict[int, float] = {}

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
        """
        if embedding is None or embedding.size == 0:
            return

        # Фильтр качества — не берём грязные детекции
        if conf < self.cfg.min_conf_for_gallery:
            return

        emb = embedding.flatten().astype(np.float64)

        with self.lock:
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
        """
        with self.lock:
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
    ) -> tuple[int | None, float, str]:
        """
        Поиск совпадения нового трека среди «мёртвых» ID.
        Возвращает (ID_склейки, балл, статус)
        """
        if embedding is None or embedding.size == 0:
            return None, 0.0, "ERROR"

        emb = embedding.flatten().astype(np.float64)
        best_id = None
        best_score = -1.0
        
        # Для отладки «близких промахов»
        best_overall_id = None
        best_overall_score = -1.0

        with self.lock:
            if not self._dead_pool:
                return None, 0.0, "EMPTY"

            for old_id, data in self._dead_pool.items():
                if old_id in self._reversed_map:
                    continue

                cos_sim = _cosine_similarity(emb, data["emb"])
                
                if self.cfg.spatial_iou_weight > 0.0:
                    penalty = _spatial_penalty(data["bbox"], bbox)
                    score = cos_sim * (1.0 - self.cfg.spatial_iou_weight * penalty)
                else:
                    score = cos_sim

                # Запоминаем лучший результат в любом случае для отладки
                if score > best_overall_score:
                    best_overall_score = score
                    best_overall_id = old_id

                # Порог проверяем для РЕАЛЬНОЙ склейки
                if score >= self.cfg.similarity_threshold:
                    if score > best_score:
                        best_score = score
                        best_id = old_id

            if best_id is not None:
                self._reversed_map[best_id] = new_id
                logger.info(f"[ReIDGallery] Склейка: {new_id} → {best_id} (sc:{best_score:.3f})")
                return best_id, best_score, "SUCCESS"
            
            # Если склейка не прошла, но был сильный кандидат (> 0.5)
            if best_overall_id is not None and best_overall_score > 0.5:
                return best_overall_id, best_overall_score, "REJECTED"

        return None, 0.0, "NONE"

    def apply_alias(self, track_id: int) -> int:
        """
        Применить alias_map к track_id.
        Рекурсивно раскрывает цепочки алиасов с оптимизацией Path Compression.
        """
        with self.lock:
            if track_id not in self.alias_map:
                return track_id

            visited = set()
            current = track_id
            path = []
            while current in self.alias_map and current not in visited:
                path.append(current)
                visited.add(current)
                current = self.alias_map[current]
            
            # Path Compression: записываем финальный ID для всех узлов пути
            for node in path:
                self.alias_map[node] = current
                
            return current
    
    def cleanup(self) -> None:
        """Удалить устаревшие записи из dead_pool и очистить alias_map."""
        now = time.time()
        with self.lock:
            # 1. Очистка мёртвого пула
            expired = [
                tid for tid, data in self._dead_pool.items()
                if (now - data["ts"]) > self.cfg.max_age_seconds
            ]
            for tid in expired:
                del self._dead_pool[tid]
                self._reversed_map.pop(tid, None)

            # 2. Очистка alias_map
            # Удаляем старые алиасы, которые ведут к ID, которых больше нет в памяти ReID.
            # Если мы забыли эмбеддинг ID, мы всё равно не сможем к нему больше приклеиться.
            to_delete = []
            if self.alias_map:
                # Множество всех "полезных" ID в системе ReID
                known_ids = set(self._live_embeddings.keys()) | set(self._dead_pool.keys())
                
                for start_id in self.alias_map.keys():
                    # canonical — это конец цепочки (старейший ID)
                    canonical = self.apply_alias(start_id)
                    if canonical not in known_ids:
                        to_delete.append(start_id)
                
                for tid in to_delete:
                    self.alias_map.pop(tid, None)
                    self.stitch_scores.pop(tid, None)

            if expired or to_delete:
                logger.debug(
                    f"[ReIDGallery] Очистка: удалено {len(expired)} эмбеддингов, "
                    f"{len(to_delete)} алиасов"
                )

    def remove_track(self, track_id: int) -> None:
        """
        Принудительное удаление трека из всех внутренних структур.
        Вызывается при эвикции трека из основного хранилища (LRU).
        """
        with self.lock:
            self._live_embeddings.pop(track_id, None)
            self._dead_pool.pop(track_id, None)
            self._reversed_map.pop(track_id, None)
            # Мы не трогаем alias_map, чтобы сохранить цепочки склеек для активных ID

    def extract_embeddings_from_tracker(self, tracker) -> dict[int, np.ndarray]:
        """
        Извлечение текущих эмбеддингов из внутренних структур BoxMOT-трекера.
        Поддерживает трекеры с атрибутом active_tracks или tracked_stracks.
        """
        result = {}

        # 1. Поиск атрибута со списком треков
        # (Проверяем оба на случай кастомных сборок или смены версий)
        tracks_list = []
        if hasattr(tracker, "active_tracks"):
            tracks_list.extend(tracker.active_tracks)
        if hasattr(tracker, "tracked_stracks"):
            # Добавляем только те, которых еще нет в списке по ID
            existing_ids = {getattr(t, "id", getattr(t, "track_id", None)) for t in tracks_list}
            for t in tracker.tracked_stracks:
                tid = getattr(t, "track_id", getattr(t, "id", None))
                if tid not in existing_ids:
                    tracks_list.append(t)

        # 2. Извлечение данных из объектов
        for trk in tracks_list:
            # Пытаемся получить ID (разные трекеры используют id или track_id)
            tid = getattr(trk, "id", getattr(trk, "track_id", None))
            # Пытаемся получить эмбеддинг (smooth_feat — стандарт для BoTSORT/HybridSort)
            feat = getattr(trk, "smooth_feat", getattr(trk, "curr_feat", None))
            
            if tid is not None and feat is not None:
                result[tid] = np.array(feat, dtype=np.float64)

        return result
