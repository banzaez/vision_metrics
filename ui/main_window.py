import json
import os
import logging
import config
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QSizePolicy, QMessageBox, QTabWidget)
from PyQt6.QtGui import QImage, QPixmap, QShortcut, QKeySequence
from PyQt6.QtCore import Qt, pyqtSlot, QTimer

# Импорт вынесенных UI-компонентов
from ui.regions_panel import RegionsPanel
from ui.stats_panel import StatsPanel
from ui.video_controls import VideoControlPanel
from ui.resource_monitor import ResourceMonitorWidget
from ui.engine_status import EngineStatusWidget
from ui.json_inspector import JsonInspectorWidget

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
        
        # Таймер для сохранения настроек окна с задержкой (чтобы не писать на диск слишком часто)
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_window_settings)
        
        # Основной виджет и Layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)

        # ЛЕВАЯ ЧАСТЬ: Левая панель с общим монитором и вкладками
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        # ПАНЕЛЬ МОНИТОРИНГА РЕСУРСОВ (Общая для всех вкладок)
        self.perf_monitor = ResourceMonitorWidget()
        if not config.settings.system.ui.show_monitoring:
            self.perf_monitor.hide()
        self.left_layout.addWidget(self.perf_monitor)

        # Вкладки
        self.tabs = QTabWidget()
        self.left_layout.addWidget(self.tabs)
        
        # Вкладка 1: Видео монитор
        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 5, 0, 0)
        
        # ПАНЕЛЬ СТАТУСА МОДЕЛЕЙ (Engine Status)
        self.engine_status = EngineStatusWidget()
        self.video_layout.addWidget(self.engine_status)

        self.video_label = QLabel("Stream Loading...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Используем Ignored, чтобы QLabel не увеличивал окно при установке Pixmap
        self.video_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.video_layout.addWidget(self.video_label, stretch=1)
        
        # Панель управления видео (пауза, перемотка)
        self.video_controls = VideoControlPanel(self.video_worker)
        self.video_layout.setSpacing(0) # Убираем зазор между монитором, видео и контролами
        self.video_layout.addWidget(self.video_controls, stretch=0)
        
        # Добавляем вкладку видео
        self.tabs.addTab(self.video_container, "Live Video")
        
        # Вкладка 2: Инспектор данных JSON
        self.json_inspector = JsonInspectorWidget()
        # Убираем внутренние рамки группы для полноэкранной вкладки
        self.json_inspector.setStyleSheet("QGroupBox { border: none; }")
        self.tabs.addTab(self.json_inspector, "JSON Data")
        
        self.main_layout.addWidget(self.left_panel, 7)

        # ПРАВАЯ ЧАСТЬ: Настройки и Статистика
        self.side_panel = QWidget()
        self.side_layout = QVBoxLayout(self.side_panel)
        
        # Компонент управления регионами
        self.regions_panel = RegionsPanel(self.video_worker)
        self.side_layout.addWidget(self.regions_panel)
        
        # Компонент мониторинга (статистика)
        self.stats_panel = StatsPanel()
        self.side_layout.addWidget(self.stats_panel)

        self.main_layout.addWidget(self.side_panel, 3)

        # Восстановление настроек окна
        self.load_window_settings()

        # Подключение сигналов от воркера к UI-обновлениям.
        # Используем QueuedConnection для безопасной передачи данных между потоками.
        self.video_worker.frame_ready.connect(self.update_frame, Qt.ConnectionType.QueuedConnection)
        self.video_worker.stats_updated.connect(self.stats_panel.update_stats, Qt.ConnectionType.QueuedConnection)
        self.video_worker.json_data_ready.connect(self.json_inspector.update_json, Qt.ConnectionType.QueuedConnection)
        self.video_worker.performance_updated.connect(self.perf_monitor.update_metrics, Qt.ConnectionType.QueuedConnection)
        self.video_worker.error_occurred.connect(self.show_error, Qt.ConnectionType.QueuedConnection)
        
        # Настройка горячих клавиш через QShortcut (работают независимо от фокуса)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.video_controls.trigger_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.video_controls.step_backward)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.video_controls.step_forward)

    def load_window_settings(self):
        """Загружает положение и размер окна из файла настроек."""
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
        """Сохраняет текущее положение и размер окна на диск."""
        try:
            geom = self.frameGeometry() # Используем frameGeometry чтобы учитывать заголовок окна
            s = {
                "x": geom.x(),
                "y": geom.y(),
                "w": geom.width(),
                "h": geom.height()
            }
            filepath = config.settings.paths.window_settings_file
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(s, f)
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек окна: {e}")

    def moveEvent(self, event):
        """Событие перемещения окна."""
        self.save_timer.start(1000) # Запуск/перезапуск таймера на 1 секунду
        super().moveEvent(event)

    def resizeEvent(self, event):
        """Событие изменения размера окна."""
        self.save_timer.start(1000)
        super().resizeEvent(event)

    @pyqtSlot(object)
    def update_frame(self, frame):
        """
        Принимает готовый кадр от VideoWorker, конвертирует в QImage 
        и обновляет QLabel. Также передает кадр в панель регионов (для выделения зон).
        """
        # Передаем кадр в панель зон по ссылке (оптимизация)
        self.regions_panel.set_current_frame(frame)
        
        # Конвертация в QImage напрямую из BGR. Оставляем одну системную копию .copy().
        h, w, ch = frame.shape
        qt_frame = QImage(frame.data, w, h, ch * w, QImage.Format.Format_BGR888).copy()
        
        # Учитываем плотность пикселей для Retina-дисплеев (Mac)
        dpr = self.devicePixelRatioF()
        label_size = self.video_label.size()
        
        if not label_size.isEmpty():
            # Масштабируем до физических пикселей экрана для максимальной четкости.
            # В PyQt6 QSize * float возвращает QSize с округлением.
            target_size = label_size * dpr
            qt_frame = qt_frame.scaled(
                target_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
        
        pixmap = QPixmap.fromImage(qt_frame)
        pixmap.setDevicePixelRatio(dpr)
        
        # Атомарная установка нового pixmap
        old_pixmap = self.video_label.pixmap()
        self.video_label.setPixmap(pixmap)
        if old_pixmap is not None:
            old_pixmap.detach()

    @pyqtSlot(str)
    def show_error(self, message):
        """Отображает критическую ошибку пользователю и закрывает приложение."""
        QMessageBox.critical(self, "Критическая ошибка", message)
        self.close()

    def closeEvent(self, event):
        """Обработка закрытия окна: корректная остановка потоков без зависаний."""
        self.save_timer.stop() 
        self.save_window_settings() 
        
        # Сигнализируем об остановке и разблокируем паузу, если она была нажата
        self.video_worker.stop()
        self.video_worker.unblock_pause() 
        
        self.worker_thread.quit()
        if not self.worker_thread.wait(3000): # Ждем макс 3 секунды
            logger.warning("Поток VideoWorker не завершился вовремя, принудительная остановка.")
            self.worker_thread.terminate()
            
        super().closeEvent(event)
