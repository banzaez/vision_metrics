from PyQt6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt


class StatsPanel(QGroupBox):
    """
    Панель статистики.
    Отображает таблицу с живым мониторингом задетектированных объектов,
    их ID, типом (сотрудник/клиент) и текущей зоной нахождения.
    """

    def __init__(self, parent=None):
        super().__init__("Detected Objects (Live)", parent)
        self._layout = QVBoxLayout(self)

        # Настройка таблицы
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Type", "Lifetime"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

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
                color = Qt.GlobalColor.yellow
            elif dtype == "CLIENT":
                color = Qt.GlobalColor.blue
            else:
                color = Qt.GlobalColor.gray

            type_item.setForeground(color)
            id_item.setForeground(Qt.GlobalColor.white)
            time_item.setForeground(Qt.GlobalColor.white)
