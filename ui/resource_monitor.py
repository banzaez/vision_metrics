from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar, QFrame
from PyQt6.QtCore import pyqtSlot
import config
from ui.style_manager import StyleManager


class ResourceMonitorWidget(QFrame):
    """
    Улучшенный виджет мониторинга ресурсов с отображением числовых значений.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(StyleManager.RESOURCE_MONITOR)
        self.setObjectName("resource_panel")

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(12, 0, 12, 0)
        self.main_layout.setSpacing(15)

        # 1. FPS
        self.fps_widget = self._create_metric_group("FPS", "fps_val", "--")
        self.main_layout.addWidget(self.fps_widget)

        # 2. INF (Inference ms)
        self.inf_widget = self._create_metric_group("INF", "inf_val", "-- ms")
        self.main_layout.addWidget(self.inf_widget)

        # 3. GPU Load %
        self.gpu_widget = self._create_metric_group("GPU", "gpu_val", "0%")
        self.main_layout.addWidget(self.gpu_widget)

        # 4. CPU
        self.cpu_widget = self._create_metric_group(
            "CPU", "cpu_val", "0%"
        )
        self.main_layout.addWidget(self.cpu_widget)

        # 5. RAM
        self.ram_widget = self._create_metric_group(
            "RAM", "ram_val", "0.0 GB"
        )
        self.main_layout.addWidget(self.ram_widget)

        # 6. Device/MPS
        self.device_widget = self._create_metric_group("DEV", "device_val", "--")
        self.main_layout.addWidget(self.device_widget)

        self.main_layout.addStretch()

    def _create_metric_group(self, title, val_name, initial_val, has_bar=False):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("title")
        layout.addWidget(title_lbl)

        if has_bar:
            bar = QProgressBar()
            bar.setFixedSize(60, 6)
            bar.setTextVisible(False)
            bar.setStyleSheet(StyleManager.PROGRESS_BAR)
            layout.addWidget(bar)

        val_lbl = QLabel(initial_val)
        val_lbl.setObjectName("value")
        # Сохраняем ссылку для обновления
        setattr(self, val_name, val_lbl)
        layout.addWidget(val_lbl)

        return container

    @pyqtSlot(dict)
    def update_metrics(self, stats):
        """Обновление значений из потока VideoWorker."""
        self.fps_val.setText(f"{stats['fps']:.1f}")
        
        # Прикладные метрики (Inference & GPU Load)
        inf_ms = stats.get('inference_ms', 0)
        self.inf_val.setText(f"{inf_ms:.1f} ms")
        
        gpu_p = int(stats.get('gpu_load', 0))
        self.gpu_val.setText(f"{gpu_p}%")

        # CPU
        cpu_p = int(stats["cpu"])
        self.cpu_val.setText(f"{cpu_p}%")

        # RAM
        ram_p = int(stats["ram_percent"])
        self.ram_val.setText(f"{stats['ram_gb']:.1f} GB")

        # Динамическая смена цвета при нагрузке (теперь на текст)
        # Для CPU и GPU
        if cpu_p > 80:
            self.cpu_val.setStyleSheet(f"color: {StyleManager.DANGER_TEXT}; font-weight: bold;")
        else:
            self.cpu_val.setStyleSheet("")
            
        if gpu_p > 85:
            self.gpu_val.setStyleSheet(f"color: {StyleManager.DANGER_TEXT}; font-weight: bold;")
        else:
            self.gpu_val.setStyleSheet("")

        # Статус устройства
        dev = config.settings.system.perf.device.upper()
        gpu_status = stats.get('gpu_status', 'OFF')
        if gpu_status == "ACTIVE":
            self.device_val.setText(f"{dev}*")
            self.device_val.setStyleSheet(f"color: {StyleManager.ACCENT}; font-weight: bold;")
        else:
            self.device_val.setText(dev)
            self.device_val.setStyleSheet("")
