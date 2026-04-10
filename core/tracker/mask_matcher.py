import numpy as np

class MaskMatcher:
    """Обеспечивает сопоставление треков BoxMOT с оригинальными детекциями YOLO для извлечения масок."""

    @staticmethod
    def match_masks(tracked_objects, boxes, masks_np):
        """
        Сопоставляет отслеженные объекты с оригинальными боксами для получения индексов масок.
        Гарантирует, что одна детекция не будет привязана к двум разным трекам.
        """
        if len(boxes) == 0:
            return []

        # Предвычисление центров и площадей YOLO-боксов
        centers_x = (boxes[:, 0] + boxes[:, 2]) * 0.5
        centers_y = (boxes[:, 1] + boxes[:, 3]) * 0.5
        box_areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

        used_indices = set()
        matches = []
        
        for obj in tracked_objects:
            tx1, ty1, tx2, ty2, track_id = obj[:5]
            tcx, tcy = (tx1 + tx2) * 0.5, (ty1 + ty2) * 0.5
            
            # Сортируем все боксы по близости к центру трека
            dists = (centers_x - tcx) ** 2 + (centers_y - tcy) ** 2
            sorted_idxs = np.argsort(dists)

            best_match_idx = -1
            best_match_iou = 0.0

            for idx in sorted_idxs:
                if idx in used_indices:
                    continue
                
                # Проверка IoU
                bx1, by1, bx2, by2 = boxes[idx]
                inter_x1, inter_y1 = max(tx1, bx1), max(ty1, by1)
                inter_x2, inter_y2 = min(tx2, bx2), min(ty2, by2)

                inter_w = max(0.0, inter_x2 - inter_x1)
                inter_h = max(0.0, inter_y2 - inter_y1)
                inter_area = inter_w * inter_h
                
                track_area = (tx2 - tx1) * (ty2 - ty1)
                box_area = box_areas[idx]
                union_area = track_area + box_area - inter_area
                iou = inter_area / union_area if union_area > 0 else 0.0

                if iou > 0.45: # Порог сопоставления
                    best_match_idx = int(idx)
                    best_match_iou = iou
                    break

            if best_match_idx != -1:
                used_indices.add(best_match_idx)
            
            matches.append((int(track_id), best_match_idx, best_match_iou))
            
        return matches
