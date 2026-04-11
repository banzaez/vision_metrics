from PyQt6.QtWidgets import (QGroupBox, QVBoxLayout, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSlot
import time

class ReIDStitchPanel(QGroupBox):
    """
    Панель лога склеек Re-ID.
    Отображает историю успешных восстановлений ID.
    """
    def __init__(self, parent=None):
        super().__init__("Re-ID Stitching Log", parent)
        self.layout = QVBoxLayout(self)
        
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: 'Courier New';")
        self.layout.addWidget(self.log_list)
        
        # Ограничиваем высоту лога, давая больше места для чтения
        self.setMaximumHeight(300)

    @pyqtSlot(dict)
    def add_event(self, event_data):
        """
        Добавляет запись о склейке в лог.
        event_data: { 'old_id': int, 'new_id': int, 'score': float }
        """
        ts = time.strftime("%H:%M:%S")
        old_id = event_data.get('old_id')
        new_id = event_data.get('new_id')
        score = event_data.get('score', 0.0)
        
        msg = f"[{ts}] Match: #{new_id} -> #{old_id}"
        if score > 0:
            msg += f" (sc:{score:.2f})"
            
        item = QListWidgetItem(msg)
        self.log_list.insertItem(0, item) # Добавляем наверх
        
        # Ограничиваем количество записей в UI
        if self.log_list.count() > 50:
            self.log_list.takeItem(self.log_list.count() - 1)
