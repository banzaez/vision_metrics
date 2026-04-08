import cv2
import json
import os
import config
from PyQt6.QtWidgets import (QVBoxLayout, QPushButton, QListWidget, 
                             QLabel, QGroupBox, QMessageBox)

class RegionsPanel(QGroupBox):
    """
    Панель управления регионами и зонами (Regions & Zones Manager).
    Обеспечивает функционал добавления, редактирования и удаления 
    рабочих зон (ROI), зон для персонала и аналитических KPI зон.
    """
    def __init__(self, video_worker, parent=None):
        super().__init__("Regions & Zones Manager", parent)
        self.video_worker = video_worker
        self.last_cv_frame = None

        self.layout = QVBoxLayout(self)
        
        # Кнопки добавления зон
        self.btn_roi = QPushButton("Set/Edit ROI")
        self.btn_staff = QPushButton("+ Add Staff Zone")
        self.btn_clear = QPushButton("Clear All Regions")
        
        # Список текущих зон
        self.zones_list = QListWidget()
        self.btn_del_selected = QPushButton("Delete Selected Zone")
        self.btn_del_selected.setStyleSheet("background-color: #442222;")

        # Подключение обработчиков
        self.btn_roi.clicked.connect(self.select_roi)
        self.btn_staff.clicked.connect(self.add_staff_zone)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_del_selected.clicked.connect(self.delete_selected_zone)
        
        # Добавление виджетов на панель
        self.layout.addWidget(self.btn_roi)
        self.layout.addWidget(self.btn_staff)
        self.layout.addWidget(QLabel("Current Zones:"))
        self.layout.addWidget(self.zones_list)
        self.layout.addWidget(self.btn_del_selected)
        self.layout.addWidget(self.btn_clear)
        
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
            config.settings.analytics.roi = None
            if os.path.exists(config.settings.paths.roi_file): 
                os.remove(config.settings.paths.roi_file)
        elif text.startswith("STAFF:"):
            idx = int(text.split()[-1]) - 1
            if 0 <= idx < len(config.settings.analytics.staff_zones):
                config.settings.analytics.staff_zones.pop(idx)
                with open(config.settings.paths.staff_zones_file, 'w', encoding='utf-8') as f:
                    json.dump(config.settings.analytics.staff_zones, f)
                self.update_zones_list()

    def select_roi(self):
        """Позволяет выделить основную рабочую область (ROI)."""
        if self.last_cv_frame is None: 
            return
            
        self.video_worker.set_paused(True)
        r = cv2.selectROI("Drawing ROI", self.last_cv_frame, False)
        if r[2] > 0 and r[3] > 0:
            new_roi = [int(r[0]), int(r[1]), int(r[0]+r[2]), int(r[1]+r[3])]
            config.settings.analytics.roi = new_roi
            with open(config.settings.paths.roi_file, 'w', encoding='utf-8') as f:
                json.dump(new_roi, f)
            self.update_zones_list()
        cv2.destroyWindow("Drawing ROI")
        self.video_worker.set_paused(False)

    def add_staff_zone(self):
        """Добавляет зону для автоматического определения персонала."""
        if self.last_cv_frame is None: 
            return
            
        self.video_worker.set_paused(True)
        r = cv2.selectROI("Drawing Staff Zone", self.last_cv_frame, False)
        if r[2] > 0 and r[3] > 0:
            new_z = [int(r[0]), int(r[1]), int(r[0]+r[2]), int(r[1]+r[3])]
            config.settings.analytics.staff_zones.append(new_z)
            with open(config.settings.paths.staff_zones_file, 'w', encoding='utf-8') as f:
                json.dump(config.settings.analytics.staff_zones, f)
            self.update_zones_list()
        cv2.destroyWindow("Drawing Staff Zone")
        self.video_worker.set_paused(False)

    def clear_all(self):
        """Очищает все созданные зоны после подтверждения пользователя."""
        reply = QMessageBox.question(self, 'Удаление зон', "Сбросить все настройки зон?", 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            config.settings.analytics.roi = None
            config.settings.analytics.staff_zones = []
            for f in [config.settings.paths.roi_file, config.settings.paths.staff_zones_file]:
                if os.path.exists(f): 
                    os.remove(f)
            self.update_zones_list()
