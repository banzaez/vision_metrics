from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSlot
import config


class VideoControlPanel(QWidget):
    """
    Панель управления видео: пауза, перемотка, текущее время, выбор режима (Live/Max Power).
    """

    def __init__(self, video_worker):
        super().__init__()
        self.video_worker = video_worker

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 0, 5, 5)
        self.main_layout.setSpacing(2)

        # ПОДСКАЗКА ПО КОНТРОЛУ
        self.lbl_hint = QLabel(self._get_hint_text())
        self.lbl_hint.setStyleSheet(
            "color: #888; font-size: 10px; font-weight: 500; font-family: sans-serif;"
        )
        self.lbl_hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.main_layout.addWidget(self.lbl_hint)

        # Основной контейнер кнопок и слайдера
        self.controls_layout = QHBoxLayout()
        self.main_layout.addLayout(self.controls_layout)

        # Кнопка Play/Pause
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setFixedWidth(80)
        self.btn_pause.setCheckable(True)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.controls_layout.addWidget(self.btn_pause)

        # Чекбокс: Режим максимальной мощности (Headless/Без UI тормозов)
        self.chk_max_speed = QCheckBox("Max Power 🚀")
        self.chk_max_speed.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.chk_max_speed.stateChanged.connect(self.toggle_max_speed)
        self.controls_layout.addWidget(self.chk_max_speed)

        # Слайдер перемотки (стилизованный под тонкую линию)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 0px;
                height: 4px;
                background: #333;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                border: 1px solid #0078d4;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #0078d4;
            }
        """)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        self.controls_layout.addWidget(self.slider)

        # Метка времени/кадров
        self.lbl_time = QLabel("0 / 0")
        self.controls_layout.addWidget(self.lbl_time)

        # Подключаем сигналы от воркера
        self.video_worker.duration_ready.connect(self.set_duration)
        self.video_worker.position_changed.connect(self.update_position)

        self.is_sliding = False
        self.total_frames = 0

    @pyqtSlot(bool)
    def toggle_pause(self, checked):
        if checked:
            self.btn_pause.setText("Play")
            self.video_worker.set_paused(True)
        else:
            self.btn_pause.setText("Pause")
            self.video_worker.set_paused(False)

    @pyqtSlot(int)
    def set_duration(self, total_frames):
        self.total_frames = total_frames
        self.slider.setRange(0, total_frames)
        self.slider.setEnabled(True)
        self.update_time_label(0)

    @pyqtSlot(int)
    def update_position(self, current_frame):
        if not self.is_sliding:
            self.slider.setValue(current_frame)
            self.update_time_label(current_frame)

    def on_slider_pressed(self):
        self.is_sliding = True

    def on_slider_released(self):
        self.is_sliding = False
        self.video_worker.set_position(self.slider.value())

    def on_slider_moved(self, pos):
        self.update_time_label(pos)

    def update_time_label(self, current):
        self.lbl_time.setText(f"{current} / {self.total_frames}")

    @pyqtSlot(int)
    def toggle_max_speed(self, state):
        """Переключает воркер в режим максимальной производительности (без отрисовки)."""
        is_enabled = state == Qt.CheckState.Checked.value
        self.video_worker.set_max_speed(is_enabled)

        # Визуальная обратная связь
        if is_enabled:
            self.lbl_hint.setText("🚀 РЕЖИМ МАКСИМАЛЬНОЙ МОЩНОСТИ ВКЛЮЧЕН (БЕЗ ВИДЕО)")
            self.lbl_hint.setStyleSheet(
                "color: #ff9800; font-size: 10px; font-weight: bold;"
            )
        else:
            self.lbl_hint.setText(self._get_hint_text())
            self.lbl_hint.setStyleSheet(
                "color: #888; font-size: 10px; font-weight: 500;"
            )

    def _get_hint_text(self):
        """Generates hint text based on actual config values."""
        step_frames = config.settings.system.ui.step_frames
        frame_rate = config.settings.system.perf.frame_rate
        step_seconds = step_frames / frame_rate
        return f"Space: пауза/старт  |  ⬅ ➡: перемотка на {step_seconds:.0f} сек ({step_frames} fr)"

    def trigger_pause(self):
        """Программное переключение паузы (для пробела)."""
        self.btn_pause.setChecked(not self.btn_pause.isChecked())
        self.toggle_pause(self.btn_pause.isChecked())

    def _step(self, frames_delta: int):
        """Общий метод для смещения позиции видео."""
        if self.total_frames > 0:
            new_pos = max(0, min(self.slider.value() + frames_delta, self.total_frames))
            self.slider.setValue(new_pos)
            self.video_worker.set_position(new_pos)
            self.update_time_label(new_pos)

    def step_forward(self, frames=None):
        """Перемотка вперед на N кадров."""
        step = frames if frames is not None else config.settings.system.ui.step_frames
        self._step(step)

    def step_backward(self, frames=None):
        """Перемотка назад на N кадров."""
        step = frames if frames is not None else config.settings.system.ui.step_frames
        self._step(-step)
