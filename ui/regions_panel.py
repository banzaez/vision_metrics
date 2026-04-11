import json
import os
import config
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QListWidget,
    QLabel,
    QFrame,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from ui.style_manager import StyleManager


class ROISelectorDialog(QDialog):
    """PyQt6-native ROI selector dialog with mouse interaction."""

    def __init__(self, frame, parent=None):
        super().__init__(parent)
        self.frame = frame
        self.rect = QRect()  # In pixmap coordinates
        self.origin = None    # In pixmap coordinates
        self.drawing = False
        self.confirmed = False
        self._pixmap_offset_x = 0
        self._pixmap_offset_y = 0

        # Setup dialog
        self.setWindowTitle("Select ROI")
        self.setModal(True)
        self.setMinimumSize(800, 600)

        # Create label for image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setCursor(Qt.CursorShape.CrossCursor)
        self.image_label.setMouseTracking(True)

        # Mouse event filter
        self.image_label.mousePressEvent = self.on_mouse_press
        self.image_label.mouseMoveEvent = self.on_mouse_move
        self.image_label.mouseReleaseEvent = self.on_mouse_release

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)
        layout.addWidget(button_box)

        # Store scale factors for frame coordinate mapping
        self._scale_factor_x = 1.0
        self._scale_factor_y = 1.0

        # Initial display
        self.update_display()

    def update_display(self, roi_rect=None):
        """Convert OpenCV frame to QPixmap and display with ROI overlay."""
        # Convert frame to QImage
        h, w, ch = self.frame.shape
        bytes_per_line = ch * w
        q_image = QImage(
            self.frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888
        )

        # Create pixmap
        pixmap = QPixmap.fromImage(q_image)

        # Calculate available space for image
        margins = self.image_label.contentsMargins()
        label_margin = self.image_label.margin()
        
        # Safe dimensions (prevent TypeError and negative sizes)
        aw = self.image_label.width() - (margins.left() + margins.right() + 2 * label_margin)
        ah = self.image_label.height() - (margins.top() + margins.bottom() + 2 * label_margin)
        
        # Fallback for initial layout
        if aw <= 8 or ah <= 8:
            aw, ah = 780, 520

        # Scale to fit dialog
        scaled_pixmap = pixmap.scaled(
            aw, ah,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Update offsets for coordinate mapping
        lw, lh = self.image_label.width(), self.image_label.height()
        pw, ph = scaled_pixmap.width(), scaled_pixmap.height()
        self._pixmap_offset_x = (lw - pw) // 2
        self._pixmap_offset_y = (lh - ph) // 2

        # Draw ROI rectangle if provided
        if roi_rect and not roi_rect.isNull():
            painter = QPainter(scaled_pixmap)
            pen = QPen(QColor(0, 255, 0), 2)
            painter.setPen(pen)
            painter.drawRect(roi_rect)
            painter.end()

        self.image_label.setPixmap(scaled_pixmap)
        self._scale_factor_x = w / pw if pw > 0 else 1.0
        self._scale_factor_y = h / ph if ph > 0 else 1.0

    def resizeEvent(self, event):
        """Handle dialog resizing to rescale the image."""
        super().resizeEvent(event)
        # Note: self.rect should ideally be normalized to survive resize, 
        # but for simplicity we just clear it or let it be for now.
        self.update_display(self.rect if not self.rect.isNull() else None)

    def _map_to_pixmap(self, pos: QPoint) -> QPoint:
        """Map label coordinates to pixmap coordinates."""
        px = pos.x() - self._pixmap_offset_x
        py = pos.y() - self._pixmap_offset_y
        return QPoint(px, py)

    def on_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = self._map_to_pixmap(event.pos())
            self.rect = QRect()
            self.drawing = True

    def on_mouse_move(self, event):
        if self.drawing:
            current = self._map_to_pixmap(event.pos())
            self.rect = QRect(self.origin, current).normalized()
            self.update_display(self.rect)

    def on_mouse_release(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            current = self._map_to_pixmap(event.pos())
            self.rect = QRect(self.origin, current).normalized()
            self.update_display(self.rect)

    def accept_selection(self):
        if not self.rect.isNull() and self.rect.width() > 5 and self.rect.height() > 5:
            self.confirmed = True
            self.accept()

    def get_roi_normalized(self):
        """Returns ROI in original frame coordinates as (x, y, x2, y2)."""
        if not self.confirmed or self.rect.isNull():
            return None

        # Convert label-relative rect points to frame coordinates
        x1 = int(self.rect.left() * self._scale_factor_x)
        y1 = int(self.rect.top() * self._scale_factor_y)
        x2 = int(self.rect.right() * self._scale_factor_x)
        y2 = int(self.rect.bottom() * self._scale_factor_y)

        # Clip to frame bounds
        h, w = self.frame.shape[:2]
        x1, x2 = max(0, min(w, x1)), max(0, min(w, x2))
        y1, y2 = max(0, min(h, y1)), max(0, min(h, y2))

        return (x1, y1, x2, y2)


class RegionsPanel(QFrame):
    """
    Панель управления регионами и зонами (Regions & Zones Manager).
    Обеспечивает функционал добавления, редактирования и удаления
    рабочих зон (ROI), зон для персонала и аналитических KPI зон.
    """

    def __init__(self, video_worker, parent=None):
        super().__init__(parent)
        self.video_worker = video_worker
        self.last_cv_frame = None

        # Стиль всей панели
        self.setStyleSheet(StyleManager.PANEL_CONTAINER)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Кастомный заголовок внутри панели
        self.header = QLabel(" REGIONS & ZONES")
        self.header.setStyleSheet(StyleManager.PANEL_HEADER)
        self.main_layout.addWidget(self.header, 0)

        # Контейнер для содержимого
        self.content_widget = QWidget()
        self.layout = QGridLayout(self.content_widget)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(8, 10, 8, 10)
        self.main_layout.addWidget(self.content_widget, 1)

        # Кнопки: единый размер и стиль
        self.btn_roi = QPushButton("Set ROI")
        self.btn_staff = QPushButton("+ Staff")
        self.btn_del_selected = QPushButton("Del")
        self.btn_clear = QPushButton("Clear All")
        
        self.btn_roi.setStyleSheet(StyleManager.ACTION_BUTTON)
        self.btn_staff.setStyleSheet(StyleManager.ACTION_BUTTON)
        self.btn_del_selected.setStyleSheet(StyleManager.DANGER_BUTTON)
        self.btn_clear.setStyleSheet(StyleManager.DANGER_BUTTON)

        _btn_min_h = 28
        for b in (self.btn_roi, self.btn_staff, self.btn_del_selected, self.btn_clear):
            b.setMinimumHeight(_btn_min_h)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        # Список текущих зон
        self.zones_list = QListWidget()
        self.zones_list.setStyleSheet(StyleManager.LIST_WIDGET)
        self.zones_list.setMinimumHeight(120)
        self.zones_list.setMaximumHeight(200)

        # Сетка: Row, Col, RowSpan, ColSpan
        self.layout.addWidget(self.btn_roi, 0, 0)
        self.layout.addWidget(self.btn_staff, 0, 1)
        self.layout.addWidget(self.zones_list, 1, 0, 1, 2)
        self.layout.addWidget(self.btn_del_selected, 2, 0)
        self.layout.addWidget(self.btn_clear, 2, 1)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)

        # Ограничиваем общую высоту всей панели (даем больше места)
        self.setMinimumHeight(240)
        self.setMaximumHeight(350)

        # Подключение обработчиков
        self.btn_roi.clicked.connect(self.select_roi)
        self.btn_staff.clicked.connect(self.add_staff_zone)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_del_selected.clicked.connect(self.delete_selected_zone)

        # Первичное обновление списка зон
        self.update_zones_list()

    def set_current_frame(self, frame):
        """Сохраняет последний кадр для использования при рисовании зон."""
        self.last_cv_frame = frame

    def update_zones_list(self):
        """Обновляет текстовый список зон в пользовательском интерфейсе."""
        self.zones_list.clear()
        if config.settings.analytics.roi:
            self.zones_list.addItem("ROI: [Working Area]")
        for i, _ in enumerate(config.settings.analytics.staff_zones):
            self.zones_list.addItem(f"STAFF: Zone {i + 1}")

    def delete_selected_zone(self):
        """Удаляет выбранную зону из списка и обновляет конфигурацию."""
        current_item = self.zones_list.currentItem()
        if not current_item:
            return

        # Диалог подтверждения удаления
        reply = QMessageBox.question(
            self,
            "Удаление зоны",
            f"Вы уверены, что хотите удалить '{current_item.text()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        text = current_item.text()
        if text.startswith("ROI:"):
            config.settings.set("analytics", "roi", None)
            if os.path.exists(config.settings.paths.roi_file):
                os.remove(config.settings.paths.roi_file)
        elif text.startswith("STAFF:"):
            try:
                # Извлекаем индекс из строки "STAFF: Zone X"
                idx = int(text.split()[-1]) - 1
                if 0 <= idx < len(config.settings.analytics.staff_zones):
                    zones = list(config.settings.analytics.staff_zones)
                    zones.pop(idx)
                    config.settings.set("analytics", "staff_zones", zones)
                    with open(
                        config.settings.paths.staff_zones_file, "w", encoding="utf-8"
                    ) as f:
                        json.dump(zones, f)
            except (ValueError, IndexError):
                pass
        
        # Обновляем список в любом случае, если была попытка удаления
        self.update_zones_list()

    def select_roi(self):
        """Позволяет выделить основную рабочую область (ROI)."""
        if self.last_cv_frame is None:
            return

        self.video_worker.set_paused(True)

        selector = ROISelectorDialog(self.last_cv_frame, self)
        result = selector.exec()

        if result == QDialog.DialogCode.Accepted:
            roi = selector.get_roi_normalized()
            if roi:
                self._on_roi_selected(roi, is_roi=True)
        else:
            self._on_selection_cancelled()

    def add_staff_zone(self):
        """Добавляет зону для автоматического определения персонала."""
        if self.last_cv_frame is None:
            return

        self.video_worker.set_paused(True)

        selector = ROISelectorDialog(self.last_cv_frame, self)
        result = selector.exec()

        if result == QDialog.DialogCode.Accepted:
            roi = selector.get_roi_normalized()
            if roi:
                self._on_roi_selected(roi, is_roi=False)
        else:
            self._on_selection_cancelled()

    def _on_roi_selected(self, r, is_roi):
        """Обработка выбранной зоны."""
        # r is now in format (x, y, x2, y2)
        x, y, x2, y2 = r
        if x2 > x and y2 > y:
            coords = [x, y, x2, y2]
            if is_roi:
                config.settings.set("analytics", "roi", coords)
                with open(config.settings.paths.roi_file, "w", encoding="utf-8") as f:
                    json.dump(coords, f)
            else:
                zones = list(config.settings.analytics.staff_zones)
                zones.append(coords)
                config.settings.set("analytics", "staff_zones", zones)
                with open(
                    config.settings.paths.staff_zones_file, "w", encoding="utf-8"
                ) as f:
                    json.dump(zones, f)
            self.update_zones_list()
        self.video_worker.set_paused(False)

    def _on_selection_cancelled(self):
        """Обработка отмены выбора зоны."""
        self.video_worker.set_paused(False)

    def clear_all(self):
        """Очищает все созданные зоны после подтверждения пользователя."""
        reply = QMessageBox.question(
            self,
            "Удаление зон",
            "Сбросить все настройки зон?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            config.settings.set("analytics", "roi", None)
            config.settings.set("analytics", "staff_zones", [])
            for f in [
                config.settings.paths.roi_file,
                config.settings.paths.staff_zones_file,
            ]:
                if os.path.exists(f):
                    os.remove(f)
            self.update_zones_list()
