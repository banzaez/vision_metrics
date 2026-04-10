import os

# ПЕРВЫМ ДЕЛОМ: Настройки среды для PyTorch/OpenCV/PyQt до любых импортов.
# Это критично для корректной работы MPS Fallback и отрисовки слоев на macOS.
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["QT_MAC_WANTS_LAYER"] = "1"

import sys
import logging
import cv2
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread
import config
from ui.main_window import MainWindow
from core.pipeline.video_worker import VideoWorker

# Настройка многопоточности OpenCV (надо вызвать до загрузки каких-либо моделей)
if hasattr(cv2, 'setNumThreads'):
    cv2.setNumThreads(config.settings.system.perf.opencv_threads)

# Инициализация централизованного логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger("VisionMetrics")

def main():
    """
    Точка входа в приложение Vision Metrics.
    """
    try:
        app = QApplication(sys.argv)
    except Exception as e:
        logger.critical(f"Критическая ошибка: Не удалось инициализировать GUI (QApplication). {e}")
        logger.info("Убедитесь, что доступен графический дисплей (X11/Wayland/Quartz) или используйте headless-режим.")
        sys.exit(1)
    
    # 1. Создание фонового потока и рабочего объекта (Worker) для обработки видео
    thread = QThread()
    worker = VideoWorker()
    worker.moveToThread(thread)
    
    # 2. Создание главного окна приложения
    window = MainWindow(thread, worker)
    
    # 3. Настройка сигналов (запуск потока автоматически запускает worker.run)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    
    # 4. Запуск интерфейса и фонового потока
    window.show()
    thread.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
