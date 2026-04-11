import logging
import numpy as np
from typing import Dict, Any

from core.tracking.reid_gallery import ReIDGallery
from core.tracking.reid_stitcher import ReIDStitcher
from core.tracking.person_data import PersonData

logger = logging.getLogger(__name__)

class IdentityManager:
    """
    Высокоуровневый менеджер личностей. 
    Инкапсулирует ReID-галерею и логику склейки (Stitching).
    """
    def __init__(self, gallery_cfg, tracks_storage: Dict[int, PersonData]):
        self.enabled = gallery_cfg.enabled
        self.gallery = ReIDGallery(gallery_cfg) if self.enabled else None
        self.stitcher = ReIDStitcher(self.gallery, tracks_storage) if self.enabled else None

    def update(self, tracked_objects: np.ndarray, tracker: Any):
        """Обновление состояний ReID на текущем кадре."""
        if not self.enabled:
            return
        
        # Очищаем временные баллы текущего кадра
        self.gallery.stitch_scores.clear()
        
        # Запускаем поиск совпадений и склейку
        self.stitcher.update(tracked_objects, tracker)

    def get_identity_metadata(self, tracker_id: int) -> Dict[str, Any]:
        """
        Возвращает финальный (канонический) ID и метаданные склейки.
        """
        if not self.enabled:
            return {"track_id": tracker_id}

        # 1. Получаем стабильный ID (если была склейка)
        canonical_id = self.gallery.apply_alias(tracker_id)
        
        metadata = {
            "track_id": canonical_id,
        }

        if canonical_id != tracker_id:
            metadata["original_id"] = tracker_id
            metadata["is_stitched"] = True

        # 2. Добавляем данные о событии склейки (если она случилась прямо сейчас)
        stitch_data = self.gallery.stitch_scores.get(tracker_id)
        if stitch_data:
            metadata.update({
                "stitch_score": stitch_data.get("score", 0.0),
                "reid_status": stitch_data.get("status", "NONE")
            })
            if stitch_data.get("status") == "REJECTED":
                metadata["is_near_miss"] = True
                metadata["potential_old_id"] = stitch_data.get("old_id")

        return metadata

    def remove_track(self, track_id: int):
        """Удаление данных трека из галереи при очистке (LRU)."""
        if self.enabled:
            self.gallery.remove_track(track_id)

    def get_pending_ids(self) -> list:
        """Возвращает список ID, которые сейчас находятся в базе ReID и ждут возвращения."""
        if not self.enabled:
            return []
        with self.gallery.lock:
            # Возвращаем список ID из dead_pool
            return list(self.gallery._dead_pool.keys())

    def get_gallery_stats(self) -> Dict[str, Any]:
        """Сводка состояния галереи для UI/логов (под lock)."""
        if not self.enabled or self.gallery is None:
            return {
                "enabled": False,
                "dead_pool_count": 0,
                "live_embeddings_count": 0,
                "alias_map_count": 0,
                "reversed_map_count": 0,
                "pending_ids": [],
                "skipped_lost_no_embedding": 0,
            }
        with self.gallery.lock:
            return {
                "enabled": True,
                "dead_pool_count": len(self.gallery._dead_pool),
                "live_embeddings_count": len(self.gallery._live_embeddings),
                "alias_map_count": len(self.gallery.alias_map),
                "reversed_map_count": len(self.gallery._reversed_map),
                "pending_ids": list(self.gallery._dead_pool.keys()),
                "skipped_lost_no_embedding": self.gallery._skipped_lost_no_embedding,
            }
