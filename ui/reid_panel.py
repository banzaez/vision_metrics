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
        Добавляет детальную запись о работе Re-ID.
        """
        ts = time.strftime("%H:%M:%S")
        old_id = event_data.get('old_id')
        new_id = event_data.get('new_id')
        score = event_data.get('score', 0.0)
        status = event_data.get('status', 'SUCCESS')
        ptype = event_data.get('type', 'PERSON').upper()
        
        if status == 'SUCCESS':
            msg = f"[{ts}] RECOVERED: #{new_id} -> #{old_id} | {ptype} (Score: {score:.2f})"
            color = "#00ff00" # Ярко-зеленый
        else:
            # Отклоненная попытка (Near-miss)
            msg = f"[{ts}] REJECTED: #{new_id} vs #{old_id} | Score: {score:.2f} < Thr"
            color = "#ffaa00" # Оранжевый
            
        item = QListWidgetItem(msg)
        item.setForeground(Qt.GlobalColor.green if status == 'SUCCESS' else Qt.GlobalColor.yellow)
        
        # Для критических отклонений (очень слабых) можно использовать серый
        if status != 'SUCCESS' and score < 0.6:
            item.setForeground(Qt.GlobalColor.gray)

        self.log_list.insertItem(0, item)
        
        if self.log_list.count() > 100:
            self.log_list.takeItem(self.log_list.count() - 1)
