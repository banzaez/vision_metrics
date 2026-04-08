from dataclasses import asdict
import logging
import numpy as np
from boxmot import BotSort, ByteTrack

import config
from config.tracker import TrackerType

logger = logging.getLogger(__name__)


class TrackingService:
    """Обертка над внешним трекером (BoxMOT) для управления жизненным циклом треков."""

    def __init__(self, device="mps"):
        self.device = device
        self.cfg_tracker = config.settings.tracker
        self.tracker = self._init_tracker()

    def _init_tracker(self):
        try:
            tracker_type = self.cfg_tracker.type
            tracker_cfg_obj = self.cfg_tracker.config
            
            # Превращаем dataclass в словарь параметров
            params = asdict(tracker_cfg_obj)
            
            # Если в конфиге трекера девайс не задан, берем переданный в сервис
            if params.get("device") is None:
                params["device"] = self.device

            if tracker_type == TrackerType.BOTSORT:
                tracker = BotSort(**params)
            elif tracker_type == TrackerType.BYTETRACK:
                tracker = ByteTrack(**params)
            else:
                raise ValueError(f"Тип трекера {tracker_type} не поддерживается.")

            logger.info(f"Трекер BoxMOT ({tracker_type.value}) инициализирован с использованием Python-конфига.")
            return tracker
        except Exception as e:
            msg = f"Ошибка инициализации BoxMOT: {e}"
            logger.error(msg)
            raise RuntimeError(msg)

    def update(self, boxes, confs, cls, frame):
        """
        Обновление трекера новыми детекциями.

        Args:
            boxes: [N, 4] numpy array
            confs: [N] numpy array
            cls: [N] numpy array
            frame: Текущий кадр (для ReID)

        Returns:
            tracked_objects: Результаты от трекера или None
        """
        if self.tracker is None or len(boxes) == 0:
            return None

        # Подготовка данных для BoxMOT [N, 6] (x1, y1, x2, y2, conf, cls)
        # Принудительно используем float64 для стабильности на Apple Silicon
        dets = np.zeros((len(boxes), 6), dtype=np.float64)
        dets[:, :4] = boxes
        dets[:, 4] = confs
        dets[:, 5] = cls

        return self.tracker.update(dets, frame)
