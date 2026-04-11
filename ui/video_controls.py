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
from ui.style_manager import StyleManager


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
        self.lbl_hint.setStyleSheet(f"color: {StyleManager.TEXT_MUTED}; font-size: 11px; font-weight: 400;")
        self.lbl_hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.main_layout.addWidget(self.lbl_hint)

        # --- ВЕРХНИЙ РЯД: Слайдер и время ---
        self.slider_layout = QHBoxLayout()
        self.slider_layout.setSpacing(10)
        self.main_layout.addLayout(self.slider_layout)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.setStyleSheet(StyleManager.SLIDER_MINIMAL)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        self.slider_layout.addWidget(self.slider)

        self.lbl_time = QLabel("0 / 0")
        self.lbl_time.setStyleSheet(StyleManager.VIDEO_TIME_LABEL)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.slider_layout.addWidget(self.lbl_time)

        # --- НИЖНИЙ РЯД: Управление и доп. опции ---
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setContentsMargins(0, 5, 0, 0)
        self.main_layout.addLayout(self.controls_layout)

        # Левая часть: Режимы
        self.modes_layout = QHBoxLayout()
        self.chk_max_speed = QCheckBox("Max Power 🚀")
        self.chk_max_speed.setStyleSheet(StyleManager.VIDEO_CHECKBOX)
        self.chk_max_speed.stateChanged.connect(self.toggle_max_speed)
        self.modes_layout.addWidget(self.chk_max_speed)
        self.controls_layout.addLayout(self.modes_layout)

        self.controls_layout.addStretch()

        # Центр: Кнопки плеера
        self.playback_layout = QHBoxLayout()
        self.playback_layout.setSpacing(4)
        
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(36, 32)
        self.btn_prev.setStyleSheet(StyleManager.ACTION_BUTTON)
        self.btn_prev.clicked.connect(self.step_backward)
        self.playback_layout.addWidget(self.btn_prev)

        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setFixedSize(48, 32)
        self.btn_pause.setStyleSheet(StyleManager.ACTION_BUTTON)
        self.btn_pause.setCheckable(True)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.playback_layout.addWidget(self.btn_pause)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(36, 32)
        self.btn_next.setStyleSheet(StyleManager.ACTION_BUTTON)
        self.btn_next.clicked.connect(self.step_forward)
        self.playback_layout.addWidget(self.btn_next)

        self.controls_layout.addLayout(self.playback_layout)

        self.controls_layout.addStretch()

        # Правая часть: Пусто для баланса (или можно добавить громкость/настройки)
        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(self.chk_max_speed.sizeHint().width())
        self.controls_layout.addWidget(self.right_spacer)

        # Подключаем сигналы от воркера
        self.video_worker.duration_ready.connect(self.set_duration)
        self.video_worker.position_changed.connect(self.update_position)

        self.is_sliding = False
        self.total_frames = 0

    @pyqtSlot(bool)
    def toggle_pause(self, checked):
        if checked:
            self.btn_pause.setText("▶")
            self.video_worker.set_paused(True)
        else:
            self.btn_pause.setText("⏸")
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
            self.lbl_hint.setStyleSheet(StyleManager.VIDEO_HINT_ACTIVE)
            self.chk_max_speed.setStyleSheet(StyleManager.VIDEO_CHECKBOX_ACTIVE)
        else:
            self.lbl_hint.setText(self._get_hint_text())
            self.lbl_hint.setStyleSheet(StyleManager.VIDEO_HINT)
            self.chk_max_speed.setStyleSheet(StyleManager.VIDEO_CHECKBOX)

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
