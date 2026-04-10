
class MaskMatcher:
    """Обеспечивает сопоставление треков BoxMOT с оригинальными детекциями YOLO для извлечения масок."""

    @staticmethod
    def match_masks(tracked_objects, boxes):
        """
        Глобальное жадное сопоставление (Global Greedy Matching).
        Находит лучшие пары во всем кадре, исключая ситуацию, когда один трек 'крадет' маску у другого.
        """
        if len(boxes) == 0 or len(tracked_objects) == 0:
            return []

        # 1. Вычисляем все возможные пары и их IoU
        candidates = []
        for t_idx, obj in enumerate(tracked_objects):
            tx1, ty1, tx2, ty2, track_id = obj[:5]
            tcx, tcy = (tx1 + tx2) * 0.5, (ty1 + ty2) * 0.5
            t_area = (tx2 - tx1) * (ty2 - ty1)

            for b_idx, box in enumerate(boxes):
                bx1, by1, bx2, by2 = box
                # IoU расчет
                ix1, iy1 = max(tx1, bx1), max(ty1, by1)
                ix2, iy2 = min(tx2, bx2), min(ty2, by2)
                iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
                inter = iw * ih
                
                b_area = (bx2 - bx1) * (by2 - by1)
                union = t_area + b_area - inter
                iou = inter / union if union > 0 else 0.0

                # Расстояние для уточнения выбора при равном IoU
                dist_sq = (tcx - (bx1 + bx2) * 0.5) ** 2 + (tcy - (by1 + by2) * 0.5) ** 2

                if iou > 0.2: # Минимальный порог для включения в список кандидатов
                    candidates.append({
                        'iou': iou,
                        'dist': dist_sq,
                        'track_id': int(track_id),
                        'box_idx': b_idx
                    })

        # 2. Сортируем кандидатов: сначала максимальный IoU, затем минимальное расстояние
        candidates.sort(key=lambda x: (x['iou'], -x['dist']), reverse=True)

        used_tracks = set()
        used_boxes = set()
        matches = []

        # 3. Жадное назначение лучших пар
        for cand in candidates:
            tid = cand['track_id']
            bidx = cand['box_idx']
            if tid in used_tracks or bidx in used_boxes:
                continue
            
            matches.append((tid, bidx, cand['iou']))
            used_tracks.add(tid)
            used_boxes.add(bidx)

        # 4. Обработка треков, для которых не нашлось маски в этом кадре
        for obj in tracked_objects:
            tid = int(obj[4])
            if tid not in used_tracks:
                matches.append((tid, -1, 0.0))

        return matches
