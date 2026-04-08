import numpy as np
import logging
import cv2
import config

logger = logging.getLogger(__name__)

class ClothingClassifier:
    """
    Классификатор одежды для определения типа персоны (персонал/клиент).
    Использует K-Means кластеризацию для поиска доминирующего цвета маски.
    """
    def __init__(self, 
                 dark_threshold=None,
                 glare_threshold=None):
        """
        Инициализация.
        :param dark_threshold: Порог яркости (0-255), ниже которого цвет считается тёмным.
        :param glare_threshold: Порог отсечения бликов (V channel в HSV).
        """
        self.cfg_ident = config.settings.analytics.ident
        self.dark_threshold = dark_threshold if dark_threshold is not None else self.cfg_ident.black_threshold
        self.glare_threshold = glare_threshold if glare_threshold is not None else self.cfg_ident.glare_threshold
        
    def is_dark_clothing(self, mask, full_frame, box=None):
        """
        Проверяет, является ли доминирующий цвет одежды темным.
        
        :param mask: Маска сегментации (кроп).
        :param full_frame: Кадр (кроп).
        :param box: Координаты box. Если None, mask и full_frame считаются кропами.
        :return: True, если доминирующий цвет тёмный.
        """
        try:
            if box is not None:
                lx1, ly1, lx2, ly2 = map(int, box)
                h_cr, w_cr = full_frame.shape[:2]

                l_rx1, l_ry1 = max(0, lx1), max(0, ly1)
                l_rx2, l_ry2 = min(w_cr, lx2), min(h_cr, ly2)

                if l_rx2 <= l_rx1 or l_ry2 <= l_ry1:
                    return False

                crop_mask = mask[l_ry1:l_ry2, l_rx1:l_rx2]
                crop_f = full_frame[l_ry1:l_ry2, l_rx1:l_rx2]
            else:
                crop_mask = mask
                crop_f = full_frame

            # ВАЖНО: Переходим в HSV для фильтрации бликов (от софитов)
            hsv = cv2.cvtColor(crop_f, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]

            # Выбираем пиксели силуэта (учитываем только те, где маска уверена > 0.5)
            # И ИСКЛЮЧАЕМ блики (V > glare_threshold), которые могут "осветлить" черную ткань
            mask_indices = (crop_mask > 0.5) & (v_channel < self.glare_threshold)

            # Используем яркость (V channel) для быстрого анализа
            person_pixels_v = hsv[mask_indices][:, 2]

            if person_pixels_v.size > 50:
                # Считаем долю темных пикселей.
                dark_pixels = np.sum(person_pixels_v < self.dark_threshold)
                dark_ratio = dark_pixels / person_pixels_v.size
                
                # Если доля темных пикселей выше порога - считаем это униформой.
                # Либо если медианная яркость очень низкая.
                if dark_ratio > self.cfg_ident.dark_ratio_threshold or np.median(person_pixels_v) < self.dark_threshold:
                    return True

        except Exception as e:
            logger.error(f"Ошибка анализа цвета: {e}")

        return False
