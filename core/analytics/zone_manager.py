import numpy as np
import cv2

class ZoneManager:
    """Управление масками персонала и именованными зонами KPI."""
    def __init__(self):
        self._staff_mask = None
        self._staff_zones_cache = None
        self._staff_mask_shape = (0, 0)
        
        # Именованные зоны для KPI (полигоны)
        self._kpi_zones = {} # {name: np.array(points, dtype=np.int32)}

    def update_staff_mask(self, staff_zones, frame_shape):
        h, w = frame_shape[:2]
        
        if (h, w) == self._staff_mask_shape and staff_zones == self._staff_zones_cache:
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

    def update_kpi_zones(self, zones_dict):
        """Обновляет словарь именованных зон (полигонов)."""
        self._kpi_zones = {}
        for name, points in zones_dict.items():
            if points:
                # Преобразуем в numpy массив для cv2.pointPolygonTest
                self._kpi_zones[name] = np.array(points, dtype=np.int32)

    def get_zone_name(self, cx, cy):
        """Возвращает имя зоны, в которой находится точка (cx, cy)."""
        for name, polygon in self._kpi_zones.items():
            # cv2.pointPolygonTest возвращает:
            # +1 если внутри, 0 если на границе, -1 если снаружи
            if cv2.pointPolygonTest(polygon, (float(cx), float(cy)), False) >= 0:
                return name
        return None

    def is_in_staff_zone(self, cx, cy):
        if self._staff_mask is not None:
            h_m, w_m = self._staff_mask_shape
            if 0 <= cy < h_m and 0 <= cx < w_m:
                return self._staff_mask[int(cy), int(cx)]
        return False
