from boxmot import (
    SFSORT, BoostTrack, OcSort, HybridSort, 
    DeepOcSort, StrongSort, BotSort, ByteTrack
)
import numpy as np
from dataclasses import asdict
import logging

import config
from config.tracker import TrackerType

logger = logging.getLogger(__name__)


class TrackingService:
    """Обертка над внешним трекером (BoxMOT) для управления жизненным циклом треков."""

    def __init__(self, device="mps", half=False):
        self.device = device
        self.half = half
        self.cfg_tracker = config.settings.tracker
        self.tracker = self._init_tracker()

    def _init_tracker(self):
        try:
            tracker_type = self.cfg_tracker.type
            tracker_cfg_obj = self.cfg_tracker.config

            # Превращаем dataclass в словарь параметров
            params = asdict(tracker_cfg_obj)

            params["device"] = self.device
            params["half"] = self.half

            params["with_reid"] = self.cfg_tracker.with_reid
            params["reid_weights"] = self.cfg_tracker.reid_model

            # Динамически вычисляем фреймрейт с учетом пропуска кадров
            cfg_perf = config.settings.system.perf
            params["frame_rate"] = cfg_perf.frame_rate // cfg_perf.frame_skip

            match tracker_type:
                case TrackerType.BOTSORT:
                    tracker = BotSort(**params)
                case TrackerType.BYTETRACK:
                    tracker = ByteTrack(**params)
                case TrackerType.BOOSTTRACK:
                    tracker = BoostTrack(**params)
                case TrackerType.STRONGSORT:
                    tracker = StrongSort(**params)
                case TrackerType.DEEPOCSORT:
                    tracker = DeepOcSort(**params)
                case TrackerType.HYBRIDSORT:
                    tracker = HybridSort(**params)
                case TrackerType.OCSORT:
                    tracker = OcSort(**params)
                case TrackerType.SFSORT:
                    tracker = SFSORT(**params)
                case _:
                    raise ValueError(f"Тип трекера {tracker_type} не поддерживается.")

            logger.info(
                f"Трекер BoxMOT ({tracker_type.value}) инициализирован с использованием Python-конфига."
            )
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
        dets = np.zeros((len(boxes), 6))
        dets[:, :4] = boxes
        dets[:, 4] = confs
        dets[:, 5] = cls

        return self.tracker.update(dets, frame)
