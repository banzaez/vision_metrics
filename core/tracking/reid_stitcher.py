from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Set, Tuple

import numpy as np
import torch

logger = logging.getLogger(__name__)

_L2_EPS = 1e-6


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(vec) + _L2_EPS
    return vec / n


class CustomReIDStitcher:
    """
    Класс для "сшивки" треков на основе внешнего вида (ReID).
    Использует alias_map для стабильности и dead_pool для предотвращения захвата чужих ID.
    """

    def __init__(
        self,
        threshold: float = 0.6,
        gallery_size: int = 100,
        ema_alpha: float = 0.6,
        stats_callback_interval: int = 15,
    ):
        self.threshold = threshold
        self.gallery_size = gallery_size
        self.ema_alpha = ema_alpha
        self.stats_callback_interval = stats_callback_interval
        self.model = None  # Передается из трекера

        # Галерея: {final_id: embedding}
        self.gallery: Dict[int, np.ndarray] = {}
        # Порядок ключей = LRU (самый старый слева)
        self._gallery_lru: OrderedDict[int, None] = OrderedDict()

        # Карта соответствия: {tracker_id: final_id}
        self.alias_map: Dict[int, int] = {}
        # Обратный индекс для быстрой очистки при эвикции: {final_id: set(tracker_id)}
        self._final_to_trackers: Dict[int, Set[int]] = {}

        self._stats_tick = 0
        self._embed_fail_logged = False

    def process(
        self,
        tracked_objects: np.ndarray,
        frame: np.ndarray,
        tracker_instance: Any = None,
        event_callback: Optional[Callable[[dict], None]] = None,
    ) -> np.ndarray:
        """
        Обработка объектов от трекера с использованием алиасов и защиты от Hijacking.
        """
        if tracked_objects.shape[0] == 0:
            return tracked_objects

        embeddings_map = self._extract_embeddings_from_tracker(tracker_instance)

        needed_indices = []
        for i, obj in enumerate(tracked_objects):
            tid = int(obj[4])
            if tid not in embeddings_map:
                needed_indices.append(i)

        if needed_indices and self.model is not None:
            boxes_to_extract = tracked_objects[needed_indices, :4]
            with torch.no_grad():
                extra_embs = self.model.get_features(boxes_to_extract, frame)
                if isinstance(extra_embs, torch.Tensor):
                    extra_embs = extra_embs.cpu().numpy()

                for idx, emb in zip(needed_indices, extra_embs):
                    tid = int(tracked_objects[idx, 4])
                    flat = np.asarray(emb, dtype=np.float64).reshape(-1)
                    embeddings_map[tid] = _l2_normalize(flat)

        active_tracker_ids = {int(obj[4]) for obj in tracked_objects}
        active_final_ids: Set[int] = set()
        for tid in active_tracker_ids:
            if tid in self.alias_map:
                active_final_ids.add(self.alias_map[tid])
            else:
                active_final_ids.add(tid)

        dead_pool_ids = set(self.gallery.keys()) - active_final_ids
        dead_pool_count = len(dead_pool_ids)

        if event_callback:
            payload: Dict[str, Any] = {
                "type": "update_stats",
                "gallery_size": len(self.gallery),
                "dead_pool_size": dead_pool_count,
            }
            full_lists = (
                self.stats_callback_interval <= 0
                or (self._stats_tick % self.stats_callback_interval == 0)
            )
            self._stats_tick += 1
            if full_lists:
                payload["gallery_ids"] = sorted(self.gallery.keys())
                payload["dead_pool_ids"] = sorted(dead_pool_ids)
            event_callback(payload)

        exclude_for_match = set(active_final_ids)

        for i in range(len(tracked_objects)):
            tracker_id = int(tracked_objects[i, 4])
            embedding = embeddings_map.get(tracker_id)

            if embedding is None:
                continue

            if tracker_id in self.alias_map:
                final_id = self.alias_map[tracker_id]
            else:
                match_id, sim = self._find_match(embedding, exclude_ids=exclude_for_match)

                if match_id is not None:
                    self._register_alias(tracker_id, match_id)
                    final_id = match_id

                    if event_callback:
                        event_callback(
                            {
                                "type": "stitch",
                                "from_id": tracker_id,
                                "to_id": match_id,
                                "confidence": sim,
                            }
                        )
                else:
                    self._register_alias(tracker_id, tracker_id)
                    final_id = tracker_id

            tracked_objects[i, 4] = final_id
            self._update_gallery(final_id, embedding)
            exclude_for_match.add(final_id)

        return tracked_objects

    def _register_alias(self, tracker_id: int, final_id: int) -> None:
        self.alias_map[tracker_id] = final_id
        self._final_to_trackers.setdefault(final_id, set()).add(tracker_id)

    def _clear_aliases_for_final(self, final_id: int) -> None:
        tids = self._final_to_trackers.pop(final_id, None)
        if not tids:
            return
        for tid in tids:
            self.alias_map.pop(tid, None)

    def _evict_oldest_gallery_entry(self) -> None:
        if not self._gallery_lru:
            return
        old_id, _ = self._gallery_lru.popitem(last=False)
        self.gallery.pop(old_id, None)
        self._clear_aliases_for_final(old_id)

    def _extract_embeddings_from_tracker(self, tracker: Any) -> Dict[int, np.ndarray]:
        """
        Извлечение эмбеддингов напрямую из внутренностей BoxMOT.
        Экономит ресурсы GPU/CPU.
        """
        embeddings: Dict[int, np.ndarray] = {}
        if tracker is None:
            return embeddings

        try:
            tracks = []
            if hasattr(tracker, "tracker") and hasattr(tracker.tracker, "tracks"):
                tracks = tracker.tracker.tracks
            elif hasattr(tracker, "active_tracks"):
                tracks = tracker.active_tracks

            for t in tracks:
                is_active = getattr(t, "time_since_update", 1) == 0
                tid = getattr(t, "id", None)

                feat = None
                for attr in ("curr_feat", "temp_feat", "features", "last_feat"):
                    if hasattr(t, attr):
                        feat = getattr(t, attr)
                        break

                if tid is not None and feat is not None and is_active:
                    if isinstance(feat, torch.Tensor):
                        feat = feat.cpu().numpy()
                    if feat.ndim > 1:
                        feat = feat.flatten()
                    flat = np.asarray(feat, dtype=np.float64).reshape(-1)
                    embeddings[int(tid)] = _l2_normalize(flat)

        except Exception as e:
            if not self._embed_fail_logged:
                self._embed_fail_logged = True
                logger.info(
                    "Не удалось извлечь эмбеддинги из трекера (%s): %s",
                    type(tracker).__name__,
                    e,
                )
            else:
                logger.debug("Не удалось извлечь эмбеддинги из трекера: %s", e)

        return embeddings

    def _find_match(
        self, embedding: np.ndarray, exclude_ids: Set[int]
    ) -> Tuple[Optional[int], float]:
        if not self.gallery:
            return None, -1.0

        ids: list[int] = []
        rows: list[np.ndarray] = []
        for fid, emb in self.gallery.items():
            if fid not in exclude_ids:
                ids.append(fid)
                rows.append(emb)

        if not rows:
            return None, -1.0

        mat = np.stack(rows, axis=0)
        sims = mat @ embedding
        j = int(np.argmax(sims))
        top = float(sims[j])
        if top > self.threshold:
            return ids[j], top
        return None, -1.0

    def _update_gallery(self, final_id: int, embedding: np.ndarray) -> None:
        if self.gallery_size <= 0:
            return
        if final_id not in self.gallery:
            while len(self.gallery) >= self.gallery_size:
                self._evict_oldest_gallery_entry()
            self.gallery[final_id] = embedding
            self._gallery_lru[final_id] = None
            self._gallery_lru.move_to_end(final_id)
        else:
            prev = self.gallery[final_id]
            self.gallery[final_id] = self.ema_alpha * prev + (1 - self.ema_alpha) * embedding
            self.gallery[final_id] = _l2_normalize(self.gallery[final_id])
            self._gallery_lru.move_to_end(final_id)
