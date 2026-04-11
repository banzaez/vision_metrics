import json
import os
import logging
import config
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QSizePolicy, QMessageBox, QTabWidget)
from PyQt6.QtGui import QImage, QPixmap, QShortcut, QKeySequence
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from ui.style_manager import StyleManager

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    Главное окно приложения Vision Metrics.
    Собирает интерфейс из панели видеонаблюдения слева и панелей управления/статистики справа.
    """
    def __init__(self, worker_thread, video_worker):
        super().__init__()
        self.setWindowTitle("Vision Metrics - Professional Dashboard")
        
        self.worker_thread = worker_thread
        self.video_worker = video_worker
        
        # Lazy-loaded UI components
        self._regions_panel = None
        self._stats_panel = None
        self._reid_panel = None
        
        # Таймер для сохранения настроек окна с задержкой
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_window_settings)
        
        # Основной виджет и Layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        # Глобальный стиль
        self.setStyleSheet(StyleManager.MAIN_WINDOW)

        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)

        # ЛЕВАЯ ЧАСТЬ
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(8)
        
        from ui.resource_monitor import ResourceMonitorWidget
        self.perf_monitor = ResourceMonitorWidget()
        if not config.settings.system.ui.show_monitoring:
            self.perf_monitor.hide()
        self.left_layout.addWidget(self.perf_monitor)

        self.tabs = QTabWidget()
        self.left_layout.addWidget(self.tabs)
        
        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        
        from ui.engine_status import EngineStatusWidget
        self.engine_status = EngineStatusWidget()
        self.video_layout.addWidget(self.engine_status)

        self.video_label = QLabel("Stream Loading...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.video_layout.addWidget(self.video_label, stretch=1)
        
        from ui.video_controls import VideoControlPanel
        self.video_controls = VideoControlPanel(self.video_worker)
        self.video_layout.setSpacing(0)
        self.video_layout.addWidget(self.video_controls, stretch=0)
        
        self.tabs.addTab(self.video_container, "Live Video")
        
        from ui.json_inspector import JsonInspectorWidget
        self.json_inspector = JsonInspectorWidget()
        self.tabs.addTab(self.json_inspector, "JSON Data")
        
        self.main_layout.addWidget(self.left_panel, 8)

        # ПРАВАЯ ЧАСТЬ
        self.side_panel = QWidget()
        self.side_layout = QVBoxLayout(self.side_panel)
        self.side_layout.setContentsMargins(0, 0, 0, 0)
        self.side_layout.setSpacing(12)
        
        # Инстанцируем панели явно для надежности
        self.side_layout.addWidget(self.regions_panel)
        self.side_layout.addWidget(self.stats_panel)
        self.side_layout.addWidget(self.reid_panel)

        self.main_layout.addWidget(self.side_panel, 2)

        self.load_window_settings()

        self.video_worker.frame_ready.connect(self.update_frame, Qt.ConnectionType.QueuedConnection)
        self.video_worker.stats_updated.connect(self.stats_panel.update_stats, Qt.ConnectionType.QueuedConnection)
        self.video_worker.json_data_ready.connect(self.json_inspector.update_json, Qt.ConnectionType.QueuedConnection)
        self.video_worker.performance_updated.connect(self.perf_monitor.update_metrics, Qt.ConnectionType.QueuedConnection)
        self.video_worker.reid_event.connect(self.reid_panel.handle_reid_event, Qt.ConnectionType.QueuedConnection)
        self.video_worker.error_occurred.connect(self.show_error, Qt.ConnectionType.QueuedConnection)
        
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.video_controls.trigger_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.video_controls.step_backward)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.video_controls.step_forward)

    @property
    def regions_panel(self):
        if self._regions_panel is None:
            from ui.regions_panel import RegionsPanel
            self._regions_panel = RegionsPanel(self.video_worker)
        return self._regions_panel

    @property
    def stats_panel(self):
        if self._stats_panel is None:
            from ui.stats_panel import StatsPanel
            self._stats_panel = StatsPanel()
        return self._stats_panel

    @property
    def reid_panel(self):
        if self._reid_panel is None:
            from ui.reid_panel import ReIDPanel
            self._reid_panel = ReIDPanel()
        return self._reid_panel

    def load_window_settings(self):
        if os.path.exists(config.settings.paths.window_settings_file):
            try:
                with open(config.settings.paths.window_settings_file, 'r') as f:
                    s = json.load(f)
                    self.move(s.get('x', 100), s.get('y', 100))
                    self.resize(s.get('w', 1280), s.get('h', 720))
            except Exception as e:
                logger.error(f"Ошибка загрузки настроек окна: {e}")
                self.resize(1280, 720)
        else:
            self.resize(1280, 720)
            self.save_window_settings()

    def save_window_settings(self):
        try:
            geom = self.frameGeometry()
            s = {"x": geom.x(), "y": geom.y(), "w": geom.width(), "h": geom.height()}
            filepath = config.settings.paths.window_settings_file
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(s, f)
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек окна: {e}")

    def moveEvent(self, event):
        self.save_timer.start(1000)
        super().moveEvent(event)

    def resizeEvent(self, event):
        self.save_timer.start(1000)
        super().resizeEvent(event)

    @pyqtSlot(object)
    def update_frame(self, frame):
        self.regions_panel.set_current_frame(frame)
        h, w, ch = frame.shape
        frame_copy = np.ascontiguousarray(frame.copy())
        qt_frame = QImage(frame_copy.data, w, h, ch * w, QImage.Format.Format_BGR888)
        dpr = self.devicePixelRatioF()
        label_size = self.video_label.size()
        if not label_size.isEmpty():
            target_size = label_size * dpr
            qt_frame = qt_frame.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        pixmap = QPixmap.fromImage(qt_frame)
        pixmap.setDevicePixelRatio(dpr)
        self.video_label.setPixmap(pixmap)

    @pyqtSlot(str)
    def show_error(self, message):
        QMessageBox.critical(self, "Критическая ошибка", message)
        self.close()

    def closeEvent(self, event):
        self.save_timer.stop() 
        self.save_window_settings() 
        self.video_worker.stop()
        self.video_worker.unblock_pause() 
        self.worker_thread.quit()
        if not self.worker_thread.wait(3000):
            self.worker_thread.terminate()
        super().closeEvent(event)
