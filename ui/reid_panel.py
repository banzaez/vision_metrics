from PyQt6.QtWidgets import (
    QFrame,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor
from ui.style_manager import StyleManager


class ReIDPanel(QFrame):
    """
    Панель мониторинга ReID.
    Отображает логи сшивки (Stitching) и списки ID в галерее и Dead Pool.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Стиль всей панели
        self.setStyleSheet(StyleManager.PANEL_CONTAINER)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Кастомный заголовок
        self.header = QLabel(" CUSTOM RE-ID MONITOR")
        self.header.setStyleSheet(StyleManager.PANEL_HEADER)
        self.main_layout.addWidget(self.header, 0)

        # Контейнер для содержимого
        self.content_widget = QWidget()
        self._layout = QVBoxLayout(self.content_widget)
        self._layout.setContentsMargins(8, 10, 8, 10)
        self._layout.setSpacing(10)
        self.main_layout.addWidget(self.content_widget, 1)

        # Панель статистики (Gallery / DeadPool)
        self.stats_layout = QHBoxLayout()
        
        self.gallery_widget = self._create_stat_widget("Gallery History", "0")
        self.deadpool_widget = self._create_stat_widget("Dead Pool (Inactive)", "0")
        
        self.stats_layout.addWidget(self.gallery_widget)
        self.stats_layout.addWidget(self.deadpool_widget)
        self._layout.addLayout(self.stats_layout)

        # Лог событий сшивки
        self.log_header = QLabel("STITCHING EVENTS")
        self.log_header.setStyleSheet(f"color: {StyleManager.TEXT_SECONDARY}; font-size: 10px; font-weight: bold;")
        self._layout.addWidget(self.log_header)

        self.event_list = QListWidget()
        self.event_list.setStyleSheet(f"""
            QListWidget {{
                background-color: #111111;
                border: 1px solid {StyleManager.BORDER_PANEL};
                border-radius: 8px;
                color: {StyleManager.TEXT_SECONDARY};
                font-size: 11px;
                padding: 2px;
            }}
            QListWidget::item {{
                padding: 3px 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            }}
        """)
        self.event_list.setSpacing(1)
        self._layout.addWidget(self.event_list)

    def _create_stat_widget(self, title, value):
        container = QFrame()
        container.setStyleSheet(f"background: {StyleManager.BG_CARD}; border-radius: 8px; border: 1px solid {StyleManager.BORDER_CARD};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        t_label = QLabel(title.upper())
        t_label.setStyleSheet(f"color: {StyleManager.TEXT_MUTED}; font-size: 9px; font-weight: bold; letter-spacing: 0.5px;")
        
        v_layout = QHBoxLayout()
        v_label = QLabel(value)
        v_label.setStyleSheet(f"color: {StyleManager.ACCENT}; font-size: 20px; font-weight: 800; font-family: 'SF Pro Display', system-ui;")
        v_layout.addWidget(v_label)
        v_layout.addStretch()
        
        # Метка для списка ID
        ids_label = QLabel("None")
        ids_label.setStyleSheet(f"color: {StyleManager.TEXT_SECONDARY}; font-size: 10px; font-family: 'SF Mono', monospace;")
        ids_label.setWordWrap(True)
        
        layout.addWidget(t_label)
        layout.addLayout(v_layout)
        layout.addWidget(ids_label)
        
        # Сохраняем ссылки для обновления
        container.value_label = v_label
        container.ids_label = ids_label
        return container

    @pyqtSlot(dict)
    def handle_reid_event(self, event):
        """
        Обработка входящих событий ReID от VideoWorker.
        """
        event_type = event.get("type")
        
        if event_type == "update_stats":
            # Обновление Галереи
            gal_size = event.get("gallery_size", 0)
            self.gallery_widget.value_label.setText(str(gal_size))

            if "gallery_ids" in event:
                gal_ids = event.get("gallery_ids", [])
                if gal_ids:
                    ids_text = ", ".join([f"#{i}" for i in gal_ids[:15]])
                    if len(gal_ids) > 15:
                        ids_text += "..."
                    self.gallery_widget.ids_label.setText(ids_text)
                else:
                    self.gallery_widget.ids_label.setText("Empty")

            # Обновление Dead Pool
            dp_size = event.get("dead_pool_size", 0)
            self.deadpool_widget.value_label.setText(str(dp_size))

            if "dead_pool_ids" in event:
                dp_ids = event.get("dead_pool_ids", [])
                if dp_ids:
                    ids_text = ", ".join([f"#{i}" for i in dp_ids[:15]])
                    if len(dp_ids) > 15:
                        ids_text += "..."
                    self.deadpool_widget.ids_label.setText(ids_text)
                else:
                    self.deadpool_widget.ids_label.setText("None")
            
        elif event_type == "stitch":
            from_id = event.get("from_id")
            to_id = event.get("to_id")
            conf = event.get("confidence", 0.0)
            
            # Лаконичный лог события
            text = f"#{from_id} ➔ #{to_id}  ({conf:.2f})"
            item = QListWidgetItem(text)
            item.setForeground(QColor(StyleManager.WARNING_TEXT))
            
            # Вставляем в начало списка
            self.event_list.insertItem(0, item)
            
            # Ограничиваем количество записей
            if self.event_list.count() > 50:
                self.event_list.takeItem(self.event_list.count() - 1)
