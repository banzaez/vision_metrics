from PyQt6.QtWidgets import (
    QFrame,
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.style_manager import StyleManager


class StatsPanel(QFrame):
    """
    Панель статистики.
    Отображает таблицу с живым мониторингом задетектированных объектов,
    их ID, типом (сотрудник/клиент) и текущей зоной нахождения.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Стиль всей панели
        self.setStyleSheet(StyleManager.PANEL_CONTAINER)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Кастомный заголовок внутри панели
        self.header = QLabel(" DETECTED OBJECTS")
        self.header.setStyleSheet(StyleManager.PANEL_HEADER)
        self.main_layout.addWidget(self.header, 0)

        # Контейнер для содержимого
        self.content_widget = QWidget()
        self._layout = QVBoxLayout(self.content_widget)
        self._layout.setContentsMargins(8, 10, 8, 10)
        self.main_layout.addWidget(self.content_widget, 1)

        # Настройка таблицы
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Type", "Lifetime"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().hide()
        
        self.table.setStyleSheet(StyleManager.TABLE_WIDGET)

        self._layout.addWidget(self.table)

    def update_stats(self, detections):
        """
        Обновляет таблицу на основе списка детекций.
        Сортировка: STAFF -> CLIENT -> RAW.
        """
        # Group by priority to avoid sorting every frame
        priority_groups = {
            0: [],  # STAFF
            1: [],  # CLIENT
            2: [],  # RAW/other
        }

        for det in detections:
            tp = det.get("type", "").upper()
            if tp == "STAFF":
                priority = 0
            elif tp == "CLIENT":
                priority = 1
            else:
                priority = 2
            priority_groups[priority].append(det)

        # Flatten in priority order without creating a new sorted list
        ordered_detections = (
            det for priority in [0, 1, 2] for det in priority_groups[priority]
        )

        self.table.setRowCount(len(detections))

        for row, det in enumerate(ordered_detections):
            tid_val = det.get("track_id", "?")
            tid = f"#{tid_val}"

            dtype = det.get("type", "person").upper()

            # Форматируем время в "ММ:СС"
            lifetime_s = det.get("lifetime", 0)
            lifetime_str = f"{int(lifetime_s // 60):02d}:{int(lifetime_s % 60):02d}"

            items = []
            for col, text in enumerate([tid, dtype, lifetime_str]):
                item = self.table.item(row, col)
                if item is None:
                    item = QTableWidgetItem(text)
                    self.table.setItem(row, col, item)
                else:
                    item.setText(text)
                items.append(item)

            # Стилизация строки
            id_item, type_item, time_item = items
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if dtype == "STAFF":
                color = QColor(StyleManager.WARNING_TEXT)
            elif dtype == "CLIENT":
                color = QColor(StyleManager.ACCENT)
            else:
                color = QColor(StyleManager.TEXT_SECONDARY)

            type_item.setForeground(color)
            id_item.setForeground(QColor(StyleManager.TEXT_PRIMARY))
            time_item.setForeground(QColor(StyleManager.TEXT_PRIMARY))
