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
        def get_priority(det):
            tp = det.get("type", "").upper()
            if tp == "STAFF":
                return 0
            if tp == "CLIENT":
                return 1
            return 2

        sorted_detections = sorted(detections, key=get_priority)
        self.table.setRowCount(len(sorted_detections))

        for row, det in enumerate(sorted_detections):
            tid = f"#{det.get('track_id', '?')}"
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
