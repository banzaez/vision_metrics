import numpy as np


def filter_detections(boxes, confs, cls, masks_np, min_size=15.0):
    """
    Фильтрация некорректных, слишком маленьких или неестественно вытянутых боксов.
    """
    if len(boxes) == 0:
        return boxes, confs, cls, masks_np
        
    w = boxes[:, 2] - boxes[:, 0]
    h = boxes[:, 3] - boxes[:, 1]
    
    aspect_ratio = h / np.where(w > 0, w, 1e-6)
    
    valid_mask = (w > min_size) & (h > min_size) & (aspect_ratio < 6.0) & (aspect_ratio > 0.1)

    boxes = boxes[valid_mask]
    confs = confs[valid_mask]
    cls = cls[valid_mask]

    if masks_np is not None:
        masks_np = masks_np[valid_mask]
        
    return boxes, confs, cls, masks_np