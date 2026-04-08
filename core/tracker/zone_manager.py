import numpy as np

class ZoneManager:
    """Управление масками и зонами персонала."""
    def __init__(self):
        self._staff_mask = None
        self._staff_zones_cache = None
        self._staff_mask_shape = (0, 0)
    
    def update_staff_mask(self, staff_zones, frame_shape):
        h, w = frame_shape[:2]
        if staff_zones == self._staff_zones_cache and (h, w) == self._staff_mask_shape:
            return
            
        if not staff_zones:
            self._staff_mask = None
            self._staff_zones_cache = None
            self._staff_mask_shape = (h, w)
            return

        self._staff_mask = np.zeros((h, w), dtype=bool)
        for sz in staff_zones:
            sx1, sy1, sx2, sy2 = sz
            sx1, sx2 = max(0, int(sx1)), min(w, int(sx2))
            sy1, sy2 = max(0, int(sy1)), min(h, int(sy2))
            if sx2 > sx1 and sy2 > sy1:
                self._staff_mask[sy1:sy2, sx1:sx2] = True
                
        self._staff_zones_cache = staff_zones.copy() if staff_zones else []
        self._staff_mask_shape = (h, w)

    def is_in_staff_zone(self, cx, cy):
        if self._staff_mask is not None:
            h_m, w_m = self._staff_mask_shape
            if 0 <= cy < h_m and 0 <= cx < w_m:
                return self._staff_mask[int(cy), int(cx)]
        return False
