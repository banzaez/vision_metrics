import time
import psutil
import os
import logging

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    Класс для отслеживания производительности: FPS, CPU, RAM и (опционально) GPU.
    """
    def __init__(self):
        self.prev_time = time.perf_counter()
        self.fps = 0.0
        self.cpu_usage = 0.0
        self.ram_usage = 0.0
        self.ram_total = 0.0
        self.ram_percent = 0.0
        self.mps_usage = 0.0 # Для Mac (MPS)
        
        self._last_sys_update = 0
        self._process = psutil.Process(os.getpid())
        
        self._process.cpu_percent()
        time.sleep(0.1)

    def update(self):
        """Обновляет показатели FPS и системных ресурсов."""
        curr_time = time.perf_counter()
        delta = curr_time - self.prev_time
        if delta > 0:
            # Сглаживание FPS (EMA)
            instant_fps = 1.0 / delta
            self.fps = 0.9 * self.fps + 0.1 * instant_fps
        self.prev_time = curr_time

        # Системные ресурсы обновляем раз в секунду, чтобы не нагружать CPU
        if curr_time - self._last_sys_update > 1.0:
            try:
                # CPU конкретного процесса (делим на кол-во ядер для % от общей мощности)
                # Первый вызов дает 0, поэтому используем интервальное измерение
                self.cpu_usage = self._process.cpu_percent() / psutil.cpu_count()
                
                # RAM конкретного процесса в ГБ (RSS - физическая память)
                process_mem = self._process.memory_info().rss
                self.ram_usage = process_mem / (1024 ** 3)
                
                # Лимит RAM (общий объем системы для прогресс-бара)
                virtual_mem = psutil.virtual_memory()
                self.ram_total = virtual_mem.total / (1024 ** 3)
                self.ram_percent = (process_mem / virtual_mem.total) * 100
                
                # Статус MPS (GPU)
                self.mps_usage = self._get_mps_usage()
                
            except Exception as e:
                logger.debug(f"Ошибка обновления метрик: {e}")
            self._last_sys_update = curr_time

    def _get_mps_usage(self):
        """
        Заглушка для получения нагрузки на MPS. 
        На macOS нет прямого API в psutil для Apple Silicon GPU.
        """
        # В реальном приложении здесь может быть вызов powermetrics (но нужен sudo)
        # Или использование замера времени инференса относительно лимита FPS.
        return 0.0

    def get_stats(self):
        """Возвращает словарь с текущими показателями."""
        return {
            'fps': self.fps,
            'cpu': self.cpu_usage,
            'ram_gb': self.ram_usage,
            'ram_total': self.ram_total,
            'ram_percent': self.ram_percent,
            'gpu': self.mps_usage
        }
