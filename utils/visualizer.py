import cv2


class Visualizer:
    """
    Класс для визуализации детекций, полигонов зон и текстовой информации
    поверх OpenCV-кадров.
    """
    def __init__(self, zones=None):
        self._zones = zones or {}
        self._draw_options = {
            'staff_zones': True,
            'roi': True,
            'bboxes': True,
            'labels': True,
            'centers': True
        }
        # Словарь цветов (BGR формат для OpenCV)
        self.colors = {
            'staff': (0, 165, 255),      # Оранжевый
            'client': (255, 0, 0),       # Синий
            'roi': (0, 255, 0),          # Зеленый
            'staff_auto': (255, 0, 255), # Фиолетовый
            'text': (255, 255, 255),     # Белый
            'bg': (30, 30, 30)           # Темно-серый
        }
        self._zones_pts = {}

    def set_option(self, key: str, value: bool) -> None:
        """Включить/выключить отрисовку элемента."""
        if key in self._draw_options:
            self._draw_options[key] = value

    def get_option(self, key: str) -> bool:
        """Получить состояние опции отрисовки."""
        return self._draw_options.get(key, True)



    def draw(self, frame, detections, roi=None, staff_auto_zones=None):
        """
        Отрисовывает все элементы на кадре.
        
        :return: Кадр с наложенной графикой
        """
        h, w = frame.shape[:2]
        scale = max(0.5, w / 1280.0)
        thickness = max(1, int(2 * scale))
        font_scale = 0.5 * scale

        frame = frame.copy()

        if self._draw_options['staff_zones'] and staff_auto_zones:
            for sz in staff_auto_zones:
                sx1, sy1, sx2, sy2 = sz
                cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), self.colors['staff_auto'], thickness)
                cv2.putText(frame, "STAFF ZONE", (sx1, sy1 - int(10*scale)), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, self.colors['staff_auto'], max(1, thickness-1))

        if self._draw_options['roi'] and roi is not None:
            rx1, ry1, rx2, ry2 = roi
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), self.colors['roi'], thickness)
            cv2.putText(frame, "WORKING AREA", (rx1, ry1 - int(15*scale)), 
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale * 1.2, self.colors['roi'], thickness)

        if self._draw_options['bboxes']:
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                track_id = det['track_id']
                ptype = det['type']
                color = self.colors.get(ptype, self.colors['client'])

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                
                if self._draw_options['labels']:
                    label_text = f"ID:{track_id} {ptype}"
                    (tw, th), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, max(1, thickness-1))
                    cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw, y1), color, -1)
                    cv2.putText(frame, label_text, (x1, y1 - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), max(1, thickness-1))

                if self._draw_options['centers']:
                    cx = (x1 + x2) // 2
                    cy = y2
                    cv2.circle(frame, (cx, cy), int(4 * scale), color, -1)

        return frame
