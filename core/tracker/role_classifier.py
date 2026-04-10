import cv2
import time
import config
from core.classifier import ClothingClassifier

class RoleClassifier:
    """Управление классификацией персонала и клиентов на базе K-Means цвета и EMA-истории."""
    def __init__(self):
        self.cfg_role = config.settings.analytics.role
        cfg_ident = config.settings.analytics.ident
        self.classifier = ClothingClassifier(dark_threshold=cfg_ident.black_threshold)
        self.dark_cache = {}
        
    def get_is_dark(self, track_id, mask_index, box, input_frame, masks_np):
        cached = self.dark_cache.get(track_id)
        current_time = time.time()
        
        if cached is not None:
            cached_value, last_update = cached
            # Кэшируем результат на 0.5 секунды (примерно 15 кадров)
            # Это исключает лишние вычисления при паузе или нелинейном воспроизведении
            if current_time - last_update < 0.5:
                return cached_value
        
        bx1, by1, bx2, by2 = map(int, box)
        h_img, w_img = input_frame.shape[:2]
        is_dark = False
        
        if bx2 > bx1 and by2 > by1:
            h_box = by2 - by1
            y1_img = by1 + int(h_box * self.cfg_role.torso_top)
            y2_img = by1 + int(h_box * self.cfg_role.torso_bottom)
            
            if y2_img > y1_img:
                crop_f = input_frame[y1_img:y2_img, bx1:bx2]
                crop_m = None
                
                if masks_np is not None:
                    h_mask, w_mask = masks_np.shape[1], masks_np.shape[2]
                    if h_mask == h_img and w_mask == w_img:
                        # Размеры совпадают (retina_masks=True) - используем прямое кадрирование
                        crop_m = masks_np[mask_index, y1_img:y2_img, bx1:bx2]
                    else:
                        # Размеры не совпадают - вычисляем коэффициенты
                        # Это запасной вариант, если retina_masks почему-то отключены
                        sw, sh = w_mask / w_img, h_mask / h_img
                        mx1, mx2 = int(bx1 * sw), int(bx2 * sw)
                        my1, my2 = int(y1_img * sh), int(y2_img * sh)
                        
                        crop_m = masks_np[mask_index, my1:my2, mx1:mx2]
                        if crop_m.shape != crop_f.shape[:2]:
                            crop_m = cv2.resize(crop_m, (crop_f.shape[1], crop_f.shape[0]), interpolation=cv2.INTER_LINEAR)
                
                is_dark = self.classifier.is_dark_clothing(crop_m, crop_f)
        
        self.dark_cache[track_id] = (is_dark, current_time)
        return is_dark

    def classify_person_type(self, is_dark, current_ema, type_history_len, 
                             in_staff_zone=False, zone_frames=0, prev_type="unknown"):
        # ЛОГИКА "ЗОНА ВАЖНЕЕ ЦВЕТА":
        # Если человек находится в зоне персонала более 5 секунд (порог в кадрах), 
        # принудительно переключаем его в STAFF, игнорируя текущий EMA и цвет.
        if in_staff_zone and zone_frames >= self.cfg_role.staff_zone_threshold_frames:
            current_ema = 1.0
            is_dark = True
        
        alpha = self.cfg_role.ema_alpha
        new_ema = alpha * (1.0 if is_dark else 0.0) + (1.0 - alpha) * current_ema
        
        # Гистерезис: удерживаем текущий статус более слабыми порогами
        staff_thr = self.cfg_role.staff_threshold
        client_thr = self.cfg_role.client_threshold
        
        if prev_type == "staff":
            staff_thr -= self.cfg_role.hysteresis  # Легче остаться персоналом
        elif prev_type == "client":
            client_thr += self.cfg_role.hysteresis # Легче остаться клиентом
            
        raw_confidence = min(1.0, max(0.0, abs(new_ema - 0.5) * 2.0))
        warmup_factor = min(1.0, type_history_len / max(1, self.cfg_role.min_eval_frames))
        calibrated_confidence = raw_confidence * warmup_factor
        
        if type_history_len < self.cfg_role.min_eval_frames:
            return "unknown", raw_confidence, calibrated_confidence, new_ema
            
        if new_ema >= staff_thr:
            return "staff", raw_confidence, calibrated_confidence, new_ema
        if new_ema <= client_thr:
            return "client", raw_confidence, calibrated_confidence, new_ema
            
        return "unknown", raw_confidence, calibrated_confidence, new_ema

    def remove_track_data(self, track_id):
        self.dark_cache.pop(track_id, None)
