from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
import config
import os

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
        yolo_name = os.path.basename(cfg_yolo.weights).replace('.pt', '').upper()
        y_val = QLabel(yolo_name)
        y_val.setObjectName("val")
        
        # Tracker
        t_lab = QLabel("Tracker:")
        t_val = QLabel(cfg_tracker.type.value.upper())
        t_val.setObjectName("val")
        
        # ReID
        r_lab = QLabel("ReID:")
        
        # Модель ReID теперь на верхнем уровне в TrackerConfig (cfg_tracker)
        # 1. Проверяем, включен ли ReID глобально
        is_on = getattr(cfg_tracker, 'with_reid', False)
        
        # 2. Проверяем поддержку процессом (ByteTrack и OCSort не используют внешние ReID модели)
        from config.tracker import TrackerType
        reid_supported = cfg_tracker.type not in [TrackerType.BYTETRACK, TrackerType.OCSORT]

        if is_on and reid_supported:
            try:
                # Достаем значение модели. Используем .value, если это Enum, 
                model_raw = getattr(cfg_tracker, 'reid_model', "OSNET")
                reid_full = model_raw.value if hasattr(model_raw, 'value') else str(model_raw)
                
                # Показываем полное название без расширения (например: CLIP_MARKET1501)
                reid_display = reid_full.replace('.pt', '').upper()
            except Exception:
                reid_display = "ON"
        else:
            reid_display = "OFF"
        
        r_val = QLabel(reid_display)
        r_val.setObjectName("val")
        
        # Сборка
        for w in [y_lab, y_val, QLabel("|"), t_lab, t_val, QLabel("|"), r_lab, r_val]:
            layout.addWidget(w)
            
        layout.addStretch()
