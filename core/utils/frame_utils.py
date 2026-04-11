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


def apply_roi_offset(boxes, x_off, y_off):
    """
    Применение смещения ROI к боксам.
    
    Args:
        boxes: Массив боксов
        x_off, y_off: Смещения
        
    Returns:
        boxes со смещением
    """
    if x_off == 0 and y_off == 0:
        return boxes
    boxes = boxes.copy()
    boxes[:, [0, 2]] += x_off
    boxes[:, [1, 3]] += y_off
    return boxes