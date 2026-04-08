from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
import config

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
        
        from config.tracker import TrackerType
        
        cfg_yolo = config.settings.yolo
        cfg_tracker = config.settings.tracker
        
        # YOLO
        y_lab = QLabel("YOLO:")
        y_val = QLabel(cfg_yolo.weights.replace('.pt', '').upper())
        y_val.setObjectName("val")
        
        # Tracker
        t_lab = QLabel("Tracker:")
        t_val = QLabel(cfg_tracker.type.value.upper())
        t_val.setObjectName("val")
        
        # ReID
        r_lab = QLabel("ReID:")
        reid_display = "OFF"
        
        # Пытаемся достать модель ReID из конфига трекера, если она там есть
        if cfg_tracker.type == TrackerType.BOTSORT:
            try:
                # В BoTSORT параметр называется reid_model
                reid_name = cfg_tracker.config.reid_model
                reid_display = reid_name.split('_')[0].upper()
            except AttributeError:
                reid_display = "OSNET"
        
        r_val = QLabel(reid_display)
        r_val.setObjectName("val")
        
        # Сборка
        for w in [y_lab, y_val, QLabel("|"), t_lab, t_val, QLabel("|"), r_lab, r_val]:
            layout.addWidget(w)
            
        layout.addStretch()
