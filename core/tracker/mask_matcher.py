import numpy as np

class MaskMatcher:
    """Обеспечивает сопоставление треков BoxMOT с оригинальными детекциями YOLO для извлечения масок."""

    @staticmethod
    def match_masks(tracked_objects, boxes, masks_np):
        """
        Сопоставляет отслеженные объекты с оригинальными боксами для получения индексов масок.
        
        Args:
            tracked_objects: Список объектов от BoxMOT [x1, y1, x2, y2, track_id, conf, cls, ...]
            boxes: Оригинальные боксы YOLO [N, 4]
            masks_np: Оригинальные маски YOLO [N, H, W]
            
        Returns:
            list: Список кортежей (track_id, original_idx, iou)
        """
        if len(boxes) == 0:
            return []

        # Предвычисление центров и площадей YOLO-боксов
        centers_x = (boxes[:, 0] + boxes[:, 2]) * 0.5
        centers_y = (boxes[:, 1] + boxes[:, 3]) * 0.5
        box_areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

        matches = []
        for obj in tracked_objects:
            tx1, ty1, tx2, ty2, track_id = obj[:5]
            tcx, tcy = (tx1 + tx2) * 0.5, (ty1 + ty2) * 0.5
            
            # Поиск ближайшего центра
            dists = (centers_x - tcx) ** 2 + (centers_y - tcy) ** 2
            best_idx = int(np.argmin(dists))

            # Проверка IoU
            best_x1, best_y1, best_x2, best_y2 = boxes[best_idx]
            inter_x1, inter_y1 = max(tx1, best_x1), max(ty1, best_y1)
            inter_x2, inter_y2 = min(tx2, best_x2), min(ty2, best_y2)

            inter_w = max(0.0, inter_x2 - inter_x1)
            inter_h = max(0.0, inter_y2 - inter_y1)
            inter_area = inter_w * inter_h
            
            track_area = (tx2 - tx1) * (ty2 - ty1)
            best_box_area = box_areas[best_idx]

            union_area = track_area + best_box_area - inter_area
            iou = inter_area / union_area if union_area > 0 else 0.0

            matches.append((int(track_id), best_idx if iou > 0.5 else -1, iou))
            
        return matches
