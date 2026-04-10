
class MaskMatcher:
    """Обеспечивает сопоставление треков BoxMOT с оригинальными детекциями YOLO для извлечения масок."""

    @staticmethod
    def match_masks(tracked_objects, boxes, iou_threshold=0.4):
        """
        Глобальное жадное сопоставление.
        :param tracked_objects: [x1, y1, x2, y2, track_id, conf, cls]
        :param boxes: Массив боксов из YOLO (x1, y1, x2, y2)
        :param iou_threshold: Порог, ниже которого сопоставление считается неверным.
        """
        if len(boxes) == 0 or len(tracked_objects) == 0:
            return []

        # Предварительно вычисляем центры и площади оригинальных боксов YOLO
        box_centers = [( (b[0] + b[2]) * 0.5, (b[1] + b[3]) * 0.5 ) for b in boxes]
        box_areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]

        candidates = []
        for t_idx, obj in enumerate(tracked_objects):
            tx1, ty1, tx2, ty2, track_id = obj[:5]
            tcx, tcy = (tx1 + tx2) * 0.5, (ty1 + ty2) * 0.5
            t_area = (tx2 - tx1) * (ty2 - ty1)

            for b_idx, box in enumerate(boxes):
                bx1, by1, bx2, by2 = box
                
                # Быстрый расчет IoU
                ix1, iy1 = max(tx1, bx1), max(ty1, by1)
                ix2, iy2 = min(tx2, bx2), min(ty2, by2)
                iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
                inter = iw * ih
                
                if inter <= 0:
                    continue
                
                union = t_area + box_areas[b_idx] - inter
                iou = inter / union if union > 0 else 0.0

                if iou > iou_threshold:
                    # Квадрат расстояния между центрами
                    bcx, bcy = box_centers[b_idx]
                    dist_sq = (tcx - bcx) ** 2 + (tcy - bcy) ** 2
                    
                    candidates.append({
                        'iou': iou,
                        'dist': dist_sq,
                        'track_id': int(track_id),
                        'box_idx': b_idx
                    })

        # Сортировка: сначала лучший IoU, при равенстве - тот, кто ближе центром
        candidates.sort(key=lambda x: (x['iou'], -x['dist']), reverse=True)

        used_tracks = set()
        used_boxes = set()
        matches = []

        for cand in candidates:
            tid, bidx = cand['track_id'], cand['box_idx']
            if tid in used_tracks or bidx in used_boxes:
                continue
            
            matches.append((tid, bidx, cand['iou']))
            used_tracks.add(tid)
            used_boxes.add(bidx)

        # Для потерянных треков возвращаем пустой индекс маски
        for obj in tracked_objects:
            tid = int(obj[4])
            if tid not in used_tracks:
                matches.append((tid, -1, 0.0))

        return matches