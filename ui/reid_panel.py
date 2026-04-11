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
        Добавляет запись о событии Re-ID в лог.
        """
        ts = time.strftime("%H:%M:%S")
        status = event_data.get('status', 'SUCCESS')

        if status == 'GALLERY_UPDATE':
            # Обновление информации о базе (сколько людей "помним")
            pending = event_data.get('pending_ids', [])
            count = len(pending)
            self.setTitle(f"Re-ID Stitching Log (Gallery: {count})")
            return

        old_id = event_data.get('old_id')
        new_id = event_data.get('new_id')
        score = event_data.get('score', 0.0)
        ptype = str(event_data.get('type', 'PERSON')).upper()
        
        if status == 'SUCCESS':
            # Успешное восстановление личности
            msg = f"[{ts}] RECOVERED: #{new_id} → #{old_id} | {ptype} (Conf: {score:.2f})"
        elif status == 'REJECTED':
            # Подозрение на совпадение, но ниже порога
            msg = f"[{ts}] REJECTED: #{new_id} ≈ #{old_id} | Match: {score:.2f} < Thr"
        else:
            return 
            
        item = QListWidgetItem(msg)
        
        # Настройка цвета текста
        if status == 'SUCCESS':
            item.setForeground(Qt.GlobalColor.green)
        else:
            if score > 0.6:
                item.setForeground(Qt.GlobalColor.yellow)
            else:
                item.setForeground(Qt.GlobalColor.gray)

        # Прокрутка к последнему событию
        self.log_list.insertItem(0, item)
        
        # Лимит строк в логе для экономии памяти
        if self.log_list.count() > 100:
            self.log_list.takeItem(self.log_list.count() - 1)
