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

            # Динамически вычисляем фреймрейт с учетом интервала обработки
            cfg_perf = config.settings.system.perf
            params["frame_rate"] = cfg_perf.frame_rate // cfg_perf.frame_interval

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
            tracked_objects: массив результатов трекера; при отсутствии треков — (0, K) ndarray
        """
        if self.tracker is None:
            return None

        # Пустой dets — штатный сценарий BoxMOT (кадр без детекций, старые треки «дотекают»)
        n = len(boxes)
        if n == 0:
            dets = np.zeros((0, 6), dtype=np.float32)
        else:
            dets = np.zeros((n, 6), dtype=np.float32)
            dets[:, :4] = boxes
            dets[:, 4] = confs
            dets[:, 5] = cls

        out = self.tracker.update(dets, frame)
        return self._normalize_tracker_output(out)

    @staticmethod
    def _normalize_tracker_output(out):
        """Приводит вывод BoxMOT к 2D ndarray для циклов по трекам."""
        if out is None:
            return np.zeros((0, 8), dtype=np.float64)
        arr = np.asarray(out, dtype=np.float64)
        if arr.size == 0:
            return np.zeros((0, 8), dtype=np.float64)
        if arr.ndim == 1:
            return arr.reshape(1, -1)
        return arr
