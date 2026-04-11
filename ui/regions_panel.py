import cv2
import json
import os
import config
import threading
from PyQt6.QtWidgets import (QVBoxLayout, QGridLayout, QPushButton, QListWidget, 
                             QLabel, QGroupBox, QMessageBox)
from PyQt6.QtCore import QObject, pyqtSignal


class ROISelector(QObject):
    finished = pyqtSignal(tuple)
    cancelled = pyqtSignal()
    
    def __init__(self, window_name, frame):
        super().__init__()
        self.window_name = window_name
        self.frame = frame
        self._running = True
        
    def cancel(self):
        self._running = False
        
    def run(self):
        r = cv2.selectROI(self.window_name, self.frame, False)
        if self._running:
            if r[2] > 0 and r[3] > 0:
                self.finished.emit(r)
            else:
                self.cancelled.emit()
        cv2.destroyWindow(self.window_name)

class RegionsPanel(QGroupBox):
    """
    Панель управления регионами и зонами (Regions & Zones Manager).
    Обеспечивает функционал добавления, редактирования и удаления 
    рабочих зон (ROI), зон для персонала и аналитических KPI зон.
    """
    def __init__(self, video_worker, parent=None):
        super().__init__("Regions & Zones", parent)
        self.video_worker = video_worker
        self.last_cv_frame = None

        self.layout = QGridLayout(self)
        self.layout.setSpacing(4)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # Кнопки: единый размер и стиль (системная тема)
        self.btn_roi = QPushButton("Set ROI")
        self.btn_staff = QPushButton("+ Staff")
        self.btn_del_selected = QPushButton("Del")
        self.btn_clear = QPushButton("Clear All")
        _btn_min_h = 28
        for b in (self.btn_roi, self.btn_staff, self.btn_del_selected, self.btn_clear):
            b.setMinimumHeight(_btn_min_h)
        
        # Список текущих зон
        self.zones_list = QListWidget()
        self.zones_list.setMaximumHeight(110) # Увеличиваем список для наглядности
        
        # Сетка: Row, Col, RowSpan, ColSpan
        self.layout.addWidget(self.btn_roi, 0, 0)
        self.layout.addWidget(self.btn_staff, 0, 1)
        self.layout.addWidget(self.zones_list, 1, 0, 1, 2)
        self.layout.addWidget(self.btn_del_selected, 2, 0)
        self.layout.addWidget(self.btn_clear, 2, 1)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)
        
        # Ограничиваем общую высоту всей панели (даем больше места)
        self.setMaximumHeight(200)

        # Подключение обработчиков
        self.btn_roi.clicked.connect(self.select_roi)
        self.btn_staff.clicked.connect(self.add_staff_zone)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_del_selected.clicked.connect(self.delete_selected_zone)
        
        # Первичное обновление списка зон
        self.update_zones_list()

    def set_current_frame(self, frame):
        """Сохраняет последний кадр для использования при рисовании зон."""
        self.last_cv_frame = frame

    def update_zones_list(self):
        """Обновляет текстовый список зон в пользовательском интерфейсе."""
        self.zones_list.clear()
        if config.settings.analytics.roi:
            self.zones_list.addItem("ROI: [Working Area]")
        for i, _ in enumerate(config.settings.analytics.staff_zones):
            self.zones_list.addItem(f"STAFF: Zone {i+1}")

    def delete_selected_zone(self):
        """Удаляет выбранную зону из списка и обновляет конфигурацию."""
        current_item = self.zones_list.currentItem()
        if not current_item: 
            return
        
        text = current_item.text()
        if text.startswith("ROI:"):
            config.settings.set('analytics', 'roi', None)
            if os.path.exists(config.settings.paths.roi_file): 
                os.remove(config.settings.paths.roi_file)
        elif text.startswith("STAFF:"):
            idx = int(text.split()[-1]) - 1
            if 0 <= idx < len(config.settings.analytics.staff_zones):
                zones = list(config.settings.analytics.staff_zones)
                zones.pop(idx)
                config.settings.set('analytics', 'staff_zones', zones)
                with open(config.settings.paths.staff_zones_file, 'w', encoding='utf-8') as f:
                    json.dump(zones, f)
                self.update_zones_list()

    def select_roi(self):
        """Позволяет выделить основную рабочую область (ROI)."""
        if self.last_cv_frame is None: 
            return
            
        self.video_worker.set_paused(True)
        
        selector = ROISelector("Drawing ROI", self.last_cv_frame)
        selector.finished.connect(lambda r: self._on_roi_selected(r, is_roi=True))
        selector.cancelled.connect(self._on_selection_cancelled)
        
        thread = threading.Thread(target=selector.run, daemon=True)
        thread.start()

    def add_staff_zone(self):
        """Добавляет зону для автоматического определения персонала."""
        if self.last_cv_frame is None: 
            return
            
        self.video_worker.set_paused(True)
        
        selector = ROISelector("Drawing Staff Zone", self.last_cv_frame)
        selector.finished.connect(lambda r: self._on_roi_selected(r, is_roi=False))
        selector.cancelled.connect(self._on_selection_cancelled)
        
        thread = threading.Thread(target=selector.run, daemon=True)
        thread.start()

    def _on_roi_selected(self, r, is_roi):
        """Обработка выбранной зоны."""
        if r[2] > 0 and r[3] > 0:
            coords = [int(r[0]), int(r[1]), int(r[0]+r[2]), int(r[1]+r[3])]
            if is_roi:
                config.settings.set('analytics', 'roi', coords)
                with open(config.settings.paths.roi_file, 'w', encoding='utf-8') as f:
                    json.dump(coords, f)
            else:
                zones = list(config.settings.analytics.staff_zones)
                zones.append(coords)
                config.settings.set('analytics', 'staff_zones', zones)
                with open(config.settings.paths.staff_zones_file, 'w', encoding='utf-8') as f:
                    json.dump(zones, f)
            self.update_zones_list()
        self.video_worker.set_paused(False)

    def _on_selection_cancelled(self):
        """Обработка отмены выбора зоны."""
        self.video_worker.set_paused(False)

    def clear_all(self):
        """Очищает все созданные зоны после подтверждения пользователя."""
        reply = QMessageBox.question(self, 'Удаление зон', "Сбросить все настройки зон?", 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            config.settings.set('analytics', 'roi', None)
            config.settings.set('analytics', 'staff_zones', [])
            for f in [config.settings.paths.roi_file, config.settings.paths.staff_zones_file]:
                if os.path.exists(f): 
                    os.remove(f)
            self.update_zones_list()
