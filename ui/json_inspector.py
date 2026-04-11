import json
import re
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QTextEdit,
    QFrame,
    QSplitter,
)
from PyQt6.QtCore import pyqtSlot, Qt
from ui.style_manager import StyleManager

class JsonInspectorWidget(QFrame):
    """
    Виджет для отображения JSON-структуры найденных объектов.
    Сохраняет историю последних кадров в виде удобного списка складок (истории),
    что позволяет перемещаться по недавним кадрам без чрезмерного потребления памяти.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(400) # Минимальная высота, так как теперь это вкладка
        
        # Стиль всей панели
        self.setStyleSheet(StyleManager.PANEL_CONTAINER + StyleManager.LIST_WIDGET + StyleManager.JSON_VIEWER)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Кастомный заголовок внутри панели
        self.header = QLabel(" LIVE DATA INSPECTOR")
        self.header.setStyleSheet(StyleManager.PANEL_HEADER)
        self.main_layout.addWidget(self.header, 0)

        # Контейнер для содержимого
        self.content_widget = QWidget()
        layout = QHBoxLayout(self.content_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.addWidget(self.content_widget, 1)

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
        self.max_history = 1000 # Ограничитель очереди (OOM защита)

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
        # Проверяем, находимся ли мы внизу списка (с небольшим допуском)
        is_at_bottom = scrollbar.value() >= (scrollbar.maximum() - 4) if scrollbar.maximum() > 0 else True
        
        # Условие авто-слежения: либо скролл внизу, либо ничего еще не выбрано
        is_tracking = is_at_bottom and (self.frame_list.currentRow() == self.frame_list.count() - 1 or self.frame_list.currentRow() == -1)

        # Добавляем в UI список
        item_text = f"Frame {frame_id}"
        self.frame_list.addItem(item_text)

        # ОГРАНИЧЕНИЕ ИСТОРИИ (OOM Защита)
        if self.frame_list.count() > self.max_history:
            old_item = self.frame_list.takeItem(0)
            if old_item:
                try:
                    old_frame_id = int(old_item.text().replace("Frame ", ""))
                    self.history.pop(old_frame_id, None)
                except ValueError: pass

        # Авто-фокус на новых кадрах (только если мы в режиме слежения)
        if is_tracking:
            self.frame_list.setCurrentRow(self.frame_list.count() - 1)
            self.frame_list.scrollToBottom()

    def on_frame_selected(self, index):
        """Отрисовка форматированного и подкрашенного JSON при клике на элемент списка."""
        if index < 0:
            return
        item = self.frame_list.item(index)
        if item:
            frame_id = int(item.text().replace("Frame ", ""))
            data = self.history.get(frame_id)
            if data:
                # Генерируем красивый HTML с подсветкой
                html_content = self._format_json_to_html(data)
                self.json_view.setHtml(html_content)

    def _format_json_to_html(self, data):
        """Превращает JSON-объект в строку HTML с подсветкой синтаксиса."""
        raw_json = json.dumps(data, indent=2, ensure_ascii=False)
        
        # Экранируем символы HTML
        html = raw_json.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Регулярное выражение для токенов JSON
        pattern = r'("(?:[^"\\]|\\.)*")\s*(:)?|(-?\d+\.?\d*|true|false|null)'

        def colorizer(match):
            q_str, colon, literal = match.groups()
            if q_str:
                if colon: # Ключ
                    return f'<span style="color: {StyleManager.JSON_KEY}; font-weight: bold;">{q_str}</span>:'
                else: # Строковое значение
                    return f'<span style="color: {StyleManager.JSON_STRING};">{q_str}</span>'
            elif literal: # Числа, булевы значения, null
                return f'<span style="color: {StyleManager.JSON_LITERAL};">{literal}</span>'
            return match.group(0)

        highlighted = re.sub(pattern, colorizer, html)
        
        # Оборачиваем в контейнер с сохранением пробелов
        return f"""
        <div style="
            font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.4;
            white-space: pre-wrap;
            color: {StyleManager.JSON_TEXT};
        ">
        {highlighted}
        </div>
        """
