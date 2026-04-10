import json
from PyQt6.QtWidgets import (QHBoxLayout, 
                             QListWidget, QTextEdit, QGroupBox, QSplitter)
from PyQt6.QtCore import pyqtSlot, Qt

class JsonInspectorWidget(QGroupBox):
    """
    Виджет для отображения JSON-структуры найденных объектов.
    Сохраняет историю последних кадров в виде удобного списка складок (истории),
    что позволяет перемещаться по недавним кадрам без чрезмерного потребления памяти.
    """
    def __init__(self, parent=None):
        super().__init__("Live Data Inspector", parent)
        self.setMinimumHeight(400) # Минимальная высота, так как теперь это вкладка
        self.setStyleSheet("""
            QGroupBox {
                color: #aaaaaa;
                border: 1px solid #333333;
                border-radius: 4px;
                margin-top: 10px;
                background-color: #1a1a1a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QListWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #a9b7c6;
                font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
                font-size: 13px;
                border: none;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        # Левая часть — навигация по кадрам (замена вкладок)
        self.frame_list = QListWidget()
        self.frame_list.setMaximumWidth(120)
        self.frame_list.currentRowChanged.connect(self.on_frame_selected)

        # Правая часть — красивый JSON
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)

        self.splitter.addWidget(self.frame_list)
        self.splitter.addWidget(self.json_view)

        # Даем больше места JSON коду
        self.splitter.setSizes([100, 800])

        self.history = {} # frame_id -> dict
        self.max_history = 50 # Ограничитель очереди (OOM защита)

    @pyqtSlot(int, list)
    def update_json(self, frame_id, detections):
        """Пишет JSON в историю при обработке нового кадра."""
        if not detections:
            return

        # Записываем в память
        log_data = {
            "frame_id": frame_id,
            "objects": [det.copy() for det in detections]
        }
        self.history[frame_id] = log_data

        # Определяем, находимся ли мы сейчас в режиме слежения (скролл в самом низу)
        scrollbar = self.frame_list.verticalScrollBar()
        is_tracking = scrollbar.value() == scrollbar.maximum() or self.frame_list.currentRow() == -1

        # Добавляем в UI список
        item_text = f"Frame {frame_id}"
        self.frame_list.addItem(item_text)

        # ОГРАНИЧЕНИЕ ИСТОРИИ (OOM Защита)
        # Мы храним только последние 1000 кадров для живого просмотра.
        # Все данные доступны в итоговом JSON файле на диске.
        if self.frame_list.count() > 1000:
            # Удаляем старейший элемент из UI
            old_item = self.frame_list.takeItem(0)
            if old_item:
                old_frame_id = int(old_item.text().replace("Frame ", ""))
                # Удаляем из кэша данных
                self.history.pop(old_frame_id, None)

        # Авто-фокус на новых кадрах (режим живого слежения)
        if is_tracking:
            self.frame_list.scrollToBottom()
            self.frame_list.setCurrentRow(self.frame_list.count() - 1)

    def on_frame_selected(self, index):
        """Отрисовка форматированного JSON при клике на элемент списка."""
        if index < 0:
            return
        item = self.frame_list.item(index)
        if item:
            frame_id = int(item.text().replace("Frame ", ""))
            data = self.history.get(frame_id)
            if data:
                # Форматирование текста, отступы 2 пробела для компактности
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                self.json_view.setText(formatted)
