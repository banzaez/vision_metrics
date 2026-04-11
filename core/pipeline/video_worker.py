import os
import logging

# Скрываем шум декодера OpenCV (сообщения HEVC POC)
os.environ["OPENCV_VIDEOIO_LOG_LEVEL"] = "0"

from PyQt6.QtCore import QObject, pyqtSignal
import config

logger = logging.getLogger(__name__)

FRAME_SKIP_INTERVAL = 15


class VideoWorker(QObject):
    """
    Фоновый рабочий класс для обработки видеопотока.
    Инкапсулирует чтение кадров, вызов детектора, обновление аналитики и визуализацию.
    Запускается в отдельном потоке (QThread), чтобы не блокировать UI.
    """

    # Сигналы для передачи данных в UI
    frame_ready = pyqtSignal(object)  # Отправляет отрисованный кадр
    stats_updated = pyqtSignal(list)  # Отправляет список текущих детекций
    json_data_ready = pyqtSignal(int, list) # Отправляет сырые словари для JSON просмотра
    performance_updated = pyqtSignal(dict)  # Отправляет метрики CPU/RAM/FPS
    position_changed = pyqtSignal(int)  # Текущий кадр
    duration_ready = pyqtSignal(int)  # Общее кол-во кадров
    metadata_ready = pyqtSignal(dict) # Метаданные видео (FPS, разрешение и т.д.)
    error_occurred = pyqtSignal(str)  # Критическая ошибка
    reid_event = pyqtSignal(dict)   # События сшивки (stitch) и статистика галереи
    finished = pyqtSignal()  # Сигнал о завершении работы

    def __init__(self, source_index=0):
        super().__init__()
        self.source_index = source_index
        self.executor = None
        
        self.max_speed_mode = False # Режим максимальной скорости обработки без UI-отрисовки
        logger.info(f"VideoWorker инициализирован для источника #{source_index}")

    def set_max_speed(self, enabled):
        self.max_speed_mode = enabled
        if self.executor:
            self.executor.realtime = not enabled
            # Если мы в режиме макс скорости, убираем callback на кадры для экономии ресурсов
            if enabled:
                self.executor.callbacks.pop('on_frame', None)
            else:
                self.executor.callbacks['on_frame'] = self.frame_ready.emit
        logger.info(f"Режим Max Speed установлен в: {enabled}")

    def run(self):
        """Запускает универсальный экзекутор."""
        from core.pipeline.headless_executor import HeadlessExecutor
        
        cfg_sys = config.settings.system
        source = cfg_sys.video_sources[self.source_index]

        def on_stats_combined(detections):
            if detections:
                self.stats_updated.emit(detections)
                if self.executor:
                    self.json_data_ready.emit(self.executor.frame_count, detections)

        # Настройка коллбэков (мапим на сигналы PyQt)
        callbacks = {
            'on_progress': self.position_changed.emit,
            'on_performance': self.performance_updated.emit,
            'on_duration': self.duration_ready.emit,
            'on_meta': self.metadata_ready.emit,
            'on_stats': on_stats_combined,
            'on_reid': self.reid_event.emit
        }

        
        if not self.max_speed_mode:
            callbacks['on_frame'] = self.frame_ready.emit

        self.executor = HeadlessExecutor(
            source_path=source,
            batch_size=config.settings.system.perf.batch_size,
            callbacks=callbacks,
            realtime=not self.max_speed_mode
        )


        try:
            success = self.executor.run()
            if not success:
                self.error_occurred.emit("Не удалось запустить обработку видео.")
        except Exception as e:
            logger.exception(f"Критическая ошибка в VideoWorker: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def stop(self):
        if self.executor:
            self.executor.stop()

    def set_paused(self, p):
        if self.executor:
            self.executor.set_paused(p)

    def unblock_pause(self):
        if self.executor:
            self.executor._pause_event.set()

    def set_position(self, pos):
        if self.executor:
            self.executor.set_position(pos)

