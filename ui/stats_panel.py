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
        Сортировка: STAFF -> CLIENT -> GHOST.
        """
        def get_priority(det):
            if det.get("is_ghost"):
                return 2
            if det.get("type", "").upper() == "STAFF":
                return 0
            return 1

        sorted_detections = sorted(detections, key=get_priority)
        self.table.setRowCount(len(sorted_detections))

        for row, det in enumerate(sorted_detections):
            is_ghost = det.get("is_ghost", False)
            tid = f"#{det.get('track_id', '?')}"
            dtype = "GHOST" if is_ghost else det.get("type", "person").upper()

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

            if is_ghost:
                color = Qt.GlobalColor.gray
            elif dtype == "STAFF":
                color = Qt.GlobalColor.yellow
            else:
                color = Qt.GlobalColor.blue

            type_item.setForeground(color)
            id_item.setForeground(Qt.GlobalColor.white if not is_ghost else color)
            time_item.setForeground(Qt.GlobalColor.white if not is_ghost else color)
