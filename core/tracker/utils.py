import numpy as np

def crop_roi(frame, roi):
    """
    Обрезка кадра по ROI с вычислением смещения x_off, y_off.
    
    Args:
        frame: Исходный кадр (numpy array)
        roi: Список [x1, y1, x2, y2]
        
    Returns:
        tuple: (cropped_frame, x_off, y_off)
    """
    x_off, y_off = 0, 0
    input_frame = frame

    if roi and len(roi) == 4:
        x1_r, y1_r, x2_r, y2_r = roi
        h_f, w_f = frame.shape[:2]
        y1_r, y2_r = max(0, y1_r), min(h_f, y2_r)
        x1_r, x2_r = max(0, x1_r), min(w_f, x2_r)

        if y2_r > y1_r and x2_r > x1_r:
            input_frame = frame[y1_r:y2_r, x1_r:x2_r]
            x_off, y_off = x1_r, y1_r
            
    return input_frame, x_off, y_off

def filter_detections(boxes, confs, cls, masks_np, min_size=15.0):
    """
    Фильтрация некорректных, слишком маленьких или неестественно вытянутых боксов.
    """
    if len(boxes) == 0:
        return boxes, confs, cls, masks_np
        
    w = boxes[:, 2] - boxes[:, 0]
    h = boxes[:, 3] - boxes[:, 1]
    
    # Соотношение сторон (человек в полный рост обычно h/w > 1.5, но берем с запасом)
    aspect_ratio = h / np.where(w > 0, w, 1e-6)
    
    # Валидными считаем боксы достаточного размера и адекватной формы
    valid_mask = (w > min_size) & (h > min_size) & (aspect_ratio < 6.0) & (aspect_ratio > 0.1)

    boxes = boxes[valid_mask]
    confs = confs[valid_mask]
    cls = cls[valid_mask]

    if masks_np is not None:
        masks_np = masks_np[valid_mask]
        
    return boxes, confs, cls, masks_np
