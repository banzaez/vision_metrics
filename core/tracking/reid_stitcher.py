import logging
import torch
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)

class CustomReIDStitcher:
    """
    Класс для "сшивки" треков на основе внешнего вида (ReID).
    Отслеживает потерянные треки и пытается сопоставить их с новыми ID.
    """

    def __init__(self, threshold=0.6, gallery_size=100):
        self.threshold = threshold
        self.gallery_size = gallery_size
        self.model = None  # Модель будет установлена извне (из трекера)

        # Галерея: {track_id: embedding}
        self.gallery = {}
        # Очередь для эвикции старых ID из галереи (LRU-ish)
        self.id_history = deque(maxlen=gallery_size)

    def process(self, tracked_objects, frame):
        """
        Обработка объектов от трекера: извлечение эмбеддингов и сшивка.
        
        Args:
            tracked_objects: [N, 8] ndarray (x1, y1, x2, y2, track_id, conf, cls, det_ind)
            frame: Исходный кадр
            
        Returns:
            processed_objects: Тот же массив, но возможно с измененными track_id
        """
        if tracked_objects.shape[0] == 0 or self.model is None:
            return tracked_objects

        # 1. Получаем эмбеддинги (BoxMOT v16 делает кадрирование внутри)
        with torch.no_grad():
            # Извлекаем признаки для всех объектов одним батчем
            # tracked_objects[:, :4] содержит [x1, y1, x2, y2]
            embeddings = self.model.get_features(tracked_objects[:, :4], frame)
            
            if isinstance(embeddings, torch.Tensor):
                embeddings = embeddings.cpu().numpy()

        # 3. Логика сшивки (простой вариант: если ID новый, ищем в галерее)
        for i, obj in enumerate(tracked_objects):
            current_id = int(obj[4])
            current_emb = embeddings[i]
            
            # Нормализация для косинусного сходства
            current_emb = current_emb / np.linalg.norm(current_emb)

            # Если ID еще нет в галерее, возможно это "новый" ID для старого человека
            matched_id = self._find_match(current_emb, excluded_id=current_id)
            
            if matched_id is not None:
                logger.info(f"[ReIDStitcher] Сшивка трека: {current_id} -> {matched_id}")
                tracked_objects[i, 4] = matched_id
                # Обновляем эмбеддинг в галерее скользящим средним (опционально)
                self._update_gallery(matched_id, current_emb)
            else:
                # Добавляем в галерею
                self._update_gallery(current_id, current_emb)

        return tracked_objects

    def _find_match(self, embedding, excluded_id):
        best_match_id = None
        best_sim = -1.0

        for tid, gallery_emb in self.gallery.items():
            if tid == excluded_id:
                continue
                
            # Косинусное сходство (так как векторы нормализованы, это просто скалярное произведение)
            sim = np.dot(embedding, gallery_emb)
            
            if sim > self.threshold and sim > best_sim:
                best_sim = sim
                best_match_id = tid

        return best_match_id

    def _update_gallery(self, track_id, embedding):
        if track_id not in self.gallery:
            if len(self.gallery) >= self.gallery_size:
                old_id = self.id_history.popleft()
                self.gallery.pop(old_id, None)
            
            self.id_history.append(track_id)
            self.gallery[track_id] = embedding
        else:
            # Плавное обновление эмбеддинга (EMA)
            self.gallery[track_id] = 0.9 * self.gallery[track_id] + 0.1 * embedding
            self.gallery[track_id] /= np.linalg.norm(self.gallery[track_id])
