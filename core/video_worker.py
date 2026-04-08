import cv2
import os
import threading
import logging
import time

# Скрываем шум декодера OpenCV (сообщения HEVC POC)
os.environ["OPENCV_VIDEOIO_LOG_LEVEL"] = "0"

from PyQt6.QtCore import QObject, pyqtSignal
import config
from core.tracker import DetectorTracker
from utils.visualizer import Visualizer
from utils.monitor import ResourceMonitor

logger = logging.getLogger(__name__)

class VideoWorker(QObject):
    """
    Фоновый рабочий класс для обработки видеопотока.
    Инкапсулирует чтение кадров, вызов детектора, обновление аналитики и визуализацию.
    Запускается в отдельном потоке (QThread), чтобы не блокировать UI.
    """
    
    # Сигналы для передачи данных в UI
    frame_ready = pyqtSignal(object)  # Отправляет отрисованный кадр
    stats_updated = pyqtSignal(list)  # Отправляет список текущих детекций
    performance_updated = pyqtSignal(dict) # Отправляет метрики CPU/RAM/FPS
    position_changed = pyqtSignal(int) # Текущий кадр
    duration_ready = pyqtSignal(int)  # Общее кол-во кадров
    error_occurred = pyqtSignal(str)  # Критическая ошибка
    finished = pyqtSignal()           # Сигнал о завершении работы

    def __init__(self, source_index=0):
        super().__init__()
        self.source_index = source_index
        self.running = True
        self.paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._seek_position = -1
        self._batch_buffer = []

        self.detector = None
        self.visualizer = None
        self.monitor = ResourceMonitor()
        
        self.frame_count = 0
        self.last_detections = []
        logger.info(f"VideoWorker инициализирован для источника #{source_index}")

    def run(self):
        """
        Основной цикл обработки видео.
        Читает кадры, проводит инференс, собирает статистику и отправляет в UI.
        """
        # 1. Ленивая инициализация тяжелых компонентов
        try:
            cfg_yolo = config.settings.yolo
            cfg_perf = config.settings.system.perf
            
            # Инициализируем оркестратор (здесь может упасть BoxMOT)
            self.detector = DetectorTracker(cfg_yolo.weights, config.settings.analytics.camera_id, cfg_perf.device)
            self.visualizer = Visualizer()
        except Exception as e:
            msg = f"Ошибка инициализации систем анализа: {e}"
            logger.critical(msg)
            self.error_occurred.emit(msg)
            self.finished.emit()
            return

        cfg_sys = config.settings.system
        source = cfg_sys.video_sources[self.source_index]
        is_stream = not (isinstance(source, str) and os.path.isfile(source))
        
        # 0. Валидация источника (если это путь к файлу)
        if isinstance(source, str) and not any(source.startswith(p) for p in ['rtsp://', 'http://', 'https://']):
            if not os.path.exists(source):
                logger.error(f"Видеофайл не найден по пути: {os.path.abspath(source)}")
                self.finished.emit()
                return

        cap = cv2.VideoCapture(source)
        
        if not cap.isOpened():
            logger.error(f"Ошибка открытия видеоисточника (OpenCV): {source}")
            cap.release()
            self.finished.emit()
            return
        
        # Получаем информацию о видео для файлов
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if total_frames > 0:
            self.duration_ready.emit(total_frames)
            self._fps_cache = fps if fps > 0 else 25.0
            logger.info(f"Видеофайл: {total_frames} кадров, {fps} FPS")
        else:
            self._fps_cache = 25.0 # Дефолт для стримов
        
        logger.info(f"Видеопоток успешно открыт: {source}")

        cfg_perf = config.settings.system.perf
        cfg_analytics = config.settings.analytics
        cfg_ui = config.settings.system.ui

        while self.running:
            iteration_start = time.perf_counter()
            
            # Обработка перемотки
            if self._seek_position >= 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, self._seek_position)
                self.frame_count = self._seek_position
                self._seek_position = -1
                self._batch_buffer = []

            # Обработка состояния паузы
            if self.paused:
                if is_stream:
                    cap.grab()
                self._pause_event.wait(timeout=0.1)
                continue
                
            ret, frame = cap.read()
            if not ret:
                if not is_stream and self.running:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.frame_count = 0
                    continue
                break

            self.frame_count += 1
            
            # Обновляем прогресс-бар раз в 15 кадров
            if total_frames > 0 and self.frame_count % 15 == 0:
                self.position_changed.emit(self.frame_count)

            is_processing_frame = (self.frame_count % cfg_perf.frame_skip == 0)

            if is_processing_frame:
                if cfg_perf.batch_size <= 1:
                    # Стандартный режим
                    detections, active_ids = self.detector.process_frame(
                        frame,
                        frame_id=self.frame_count,
                        roi=cfg_analytics.roi, 
                        staff_zones=cfg_analytics.staff_zones
                    )
                    self._apply_detections(detections, active_ids)
                else:
                    # Пакетный режим
                    self._batch_buffer.append(frame)
                    if len(self._batch_buffer) >= cfg_perf.batch_size:
                        batch_frame_ids = list(range(self.frame_count - len(self._batch_buffer) + 1, self.frame_count + 1))
                        batch_results = self.detector.process_batch(
                            self._batch_buffer,
                            frame_ids=batch_frame_ids,
                            roi=cfg_analytics.roi,
                            staff_zones=cfg_analytics.staff_zones
                        )
                        detections, active_ids = batch_results[-1]
                        self._apply_detections(detections, active_ids)
                        self._batch_buffer = []
                    else:
                        detections = self.last_detections
            else:
                detections = self.last_detections

            # 4. Визуализация и мониторинг
            self.monitor.update()
            cfg_ui = config.settings.system.ui
            if cfg_ui.show_monitoring and self.frame_count % 10 == 0:
                self.performance_updated.emit(self.monitor.get_stats())

            vis_frame = self.visualizer.draw(
                frame, 
                detections, 
                roi=cfg_analytics.roi,
                staff_auto_zones=cfg_analytics.staff_zones
            )

            # 5. Передача результатов
            self.frame_ready.emit(vis_frame)
            
            # Для файлов добавляем адаптивную задержку, учитывая время обработки
            if not is_stream and fps > 0:
                elapsed = time.perf_counter() - iteration_start
                delay = max(0, (1 / fps) - elapsed)
                if delay > 0:
                    time.sleep(delay)

        cap.release()
        self.finished.emit()

    def _apply_detections(self, detections, active_ids):
        """Интеграция результатов детекции в UI."""
        # 1. Расчет времени жизни
        fps = getattr(self, '_fps_cache', 25.0)
        for det in detections:
            # Конвертируем разницу кадров в секунды
            lframes = det.get('lifetime_frames', 0)
            det['lifetime'] = lframes / fps if fps > 0 else 0
        
        # 2. Обновление состояния для визуализатора и UI 
        # (Прореживаем обновление статистики в таблице для экономии CPU в UI)
        self.last_detections = detections
        cfg_perf = config.settings.system.perf
        if self.frame_count % (cfg_perf.frame_skip * 3) == 0:
            self.stats_updated.emit(detections)

    def stop(self):
        """Остановка цикла обработки."""
        self.running = False

    def set_paused(self, p):
        """Постановка видеопотока на паузу."""
        self.paused = p
        if p:
            self._pause_event.clear()
        else:
            self.unblock_pause()
        logger.debug(f"Состояние паузы изменено на: {p}")

    def unblock_pause(self):
        """Разблокировка потока ожидания (используется при снятии паузы или остановке)."""
        self._pause_event.set()

    def set_position(self, pos):
        """Установка позиции воспроизведения (для файлов)."""
        self._seek_position = pos
