from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.tracking.person_data import PersonData

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Результат анализа трека."""
    person_data: PersonData
    person_dict: dict
    is_dark: bool
    type_confidence: float
    type_confidence_calibrated: float
    lifetime_frames: int


class TrackAnalyzer:
    """Анализ и классификация трека - классификация роли, цвета, EMA."""

    def __init__(self, camera_id, zone_manager, role_classifier):
        self.camera_id = camera_id
        self.zone_manager = zone_manager
        self.role_classifier = role_classifier

    def analyze(
        self,
        person_data,
        detection,
        input_frame,
        masks_np,
        frame_id,
        start_frame_id
    ):
        """
        Полный анализ трека: геометрия, зоны, классификация цвета, классификация роли.
        
        Args:
            person_data: PersonData объект
            detection: (x1, y1, x2, y2, track_id, conf, cls, det_ind)
            input_frame: исходный кадр
            masks_np: маски сегментации
            frame_id: текущий ID кадра
            start_frame_id: ID первого кадра трека
        """
        x1, y1, x2, y2 = detection[:4]
        conf = detection[5]
        det_ind = int(detection[7]) if len(detection) > 7 and 0 <= int(detection[7]) else -1

        orig_box = (x1, y1, x2, y2)
        if det_ind != -1:
            orig_box = (int(detection[0]), int(detection[1]), int(detection[2]), int(detection[3]))

        cx, y_center = (x1 + x2) // 2, y2

        in_staff_zone = self.zone_manager.is_in_staff_zone(cx, y_center)
        # Получаем имя текущей зоны (KPI зоны)
        current_zone = self.zone_manager.get_zone_name(cx, y_center)
        person_data.current_zone = current_zone

        is_dark = self.role_classifier.get_is_dark(
            person_data.track_id, det_ind, orig_box, input_frame,
            masks_np if det_ind != -1 else None,
            current_frame_id=frame_id
        )

        is_dark_history = is_dark
        person_data.history.append(is_dark_history)
        person_data.zone_frames = person_data.zone_frames + 1 if in_staff_zone else 0

        p_type, type_conf, type_conf_cal, new_ema = self.role_classifier.classify_person_type(
            is_dark_history,
            person_data.ema,
            len(person_data.history),
            in_staff_zone=in_staff_zone,
            zone_frames=person_data.zone_frames,
            prev_type=person_data.last_type
        )
        person_data.ema = new_ema
        person_data.last_type = p_type
        person_data._dirty = True

        base_dict = person_data.to_dict(person_data.start_timestamp)
        base_dict.update({
            "conf": float(conf),
            "type_confidence": type_conf,
            "type_confidence_calibrated": type_conf_cal,
            "lifetime_frames": frame_id - start_frame_id
        })

        return AnalysisResult(
            person_data=person_data,
            person_dict=base_dict,
            is_dark=is_dark,
            type_confidence=type_conf,
            type_confidence_calibrated=type_conf_cal,
            lifetime_frames=frame_id - start_frame_id
        )