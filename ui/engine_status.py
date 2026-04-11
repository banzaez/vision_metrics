from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from config.trackers.base import ReIDModel, TrackerType
from config.tracker import TrackerConfig
import config
import os


def _get_reid_display_name(cfg_tracker: TrackerConfig) -> str:
    """Safely determines ReID display name at initialization."""
    # 1. Check if ReID is globally enabled
    is_on = getattr(cfg_tracker, "with_reid", False)

    # 2. Check if tracker type supports external ReID models
    reid_supported = cfg_tracker.type not in [TrackerType.BYTETRACK, TrackerType.OCSORT]

    if not (is_on and reid_supported):
        return "OFF"

    # 3. Safely extract and format model name
    model_raw = getattr(cfg_tracker, "reid_model", ReIDModel.OSNET_X1_0.value)

    # Handle both enum and string values
    if hasattr(model_raw, "value"):
        model_str = model_raw.value
    else:
        model_str = str(model_raw)

    # Display without extension, uppercase
    return model_str.replace(".pt", "").upper()


class EngineStatusWidget(QWidget):
    """Виджет для отображения информации об активных моделях и трекере."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("engineInfo")
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget#engineInfo {
                background-color: rgba(45, 45, 45, 180);
                border-radius: 4px;
                margin-bottom: 5px;
            }
            QLabel {
                color: #aaaaaa;
                font-size: 11px;
                font-weight: bold;
            }
            QLabel#val {
                color: #4CAF50;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)

        cfg_yolo = config.settings.yolo
        cfg_tracker = config.settings.tracker

        # YOLO
        y_lab = QLabel("YOLO:")
        # Берем только имя файла (без путей) и убираем .pt
        yolo_name = os.path.basename(cfg_yolo.weights).replace(".pt", "").upper()
        y_val = QLabel(yolo_name)
        y_val.setObjectName("val")

        # Tracker
        t_lab = QLabel("Tracker:")
        t_val = QLabel(cfg_tracker.type.value.upper())
        t_val.setObjectName("val")

        # ReID
        r_lab = QLabel("ReID:")

        reid_display = _get_reid_display_name(cfg_tracker)

        r_val = QLabel(reid_display)
        r_val.setObjectName("val")

        # Сборка
        for w in [y_lab, y_val, QLabel("|"), t_lab, t_val, QLabel("|"), r_lab, r_val]:
            layout.addWidget(w)

        layout.addStretch()
