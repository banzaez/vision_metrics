from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar, QFrame
from PyQt6.QtCore import pyqtSlot

class ResourceMonitorWidget(QFrame):
    """
    Улучшенный виджет мониторинга ресурсов с отображением числовых значений.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("""
            ResourceMonitorWidget {
                background-color: #1a1a1a;
                border-bottom: 1px solid #333;
                border-radius: 6px;
            }
            QLabel {
                color: #e0e0e0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 12px;
            }
            #title { font-weight: bold; color: #888; text-transform: uppercase; font-size: 10px; }
            #value { font-weight: bold; color: #fff; min-width: 45px; }
        """)
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 0, 15, 0)
        self.main_layout.setSpacing(25)
        
        # 1. FPS
        self.fps_widget = self._create_metric_group("FPS", "fps_val", "--")
        self.main_layout.addWidget(self.fps_widget)
        
        # 2. CPU
        self.cpu_widget = self._create_metric_group("CPU", "cpu_val", "0%", has_bar=True)
        self.cpu_bar = self.cpu_widget.findChild(QProgressBar)
        self.main_layout.addWidget(self.cpu_widget)
        
        # 3. RAM
        self.ram_widget = self._create_metric_group("RAM", "ram_val", "0.0 GB", has_bar=True)
        self.ram_bar = self.ram_widget.findChild(QProgressBar)
        self.main_layout.addWidget(self.ram_widget)
        
        # 4. Device
        self.device_widget = self._create_metric_group("DEVICE", "device_val", "--")
        self.main_layout.addWidget(self.device_widget)
        
        self.main_layout.addStretch()

    def _create_metric_group(self, title, val_name, initial_val, has_bar=False):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("title")
        layout.addWidget(title_lbl)
        
        if has_bar:
            bar = QProgressBar()
            bar.setFixedSize(70, 6)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar { background-color: #333; border-radius: 3px; border: none; }
                QProgressBar::chunk { background-color: #00ff00; border-radius: 3px; }
            """)
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
        
        # CPU
        cpu_p = int(stats['cpu'])
        self.cpu_val.setText(f"{cpu_p}%")
        self.cpu_bar.setValue(cpu_p)
        
        # RAM
        ram_p = int(stats['ram_percent'])
        self.ram_val.setText(f"{stats['ram_gb']:.1f} GB")
        self.ram_bar.setValue(ram_p)
        
        # Динамическая смена цвета при нагрузке
        if cpu_p > 80:
            self.cpu_bar.setStyleSheet("QProgressBar { background-color: #333; } QProgressBar::chunk { background-color: #ff3300; }")
        else:
            self.cpu_bar.setStyleSheet("QProgressBar { background-color: #333; } QProgressBar::chunk { background-color: #00ff00; }")
            
        import config
        self.device_val.setText(config.settings.system.perf.device.upper())
