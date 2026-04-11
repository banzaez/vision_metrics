import time
import psutil
import os
import logging

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    Класс для отслеживания производительности: FPS, CPU, RAM и прикладных метрик.
    """
    def __init__(self):
        self.prev_time = time.perf_counter()
        self.fps = 0.0
        self.cpu_usage = 0.0
        self.ram_usage = 0.0
        self.ram_total = 0.0
        self.ram_percent = 0.0
        self.mps_status = "OFF"
        
        # Прикладные метрики (заполняются снаружи)
        self.inference_ms = 0.0
        self.gpu_load = 0.0
        
        self._last_sys_update = 0
        self._process = psutil.Process(os.getpid())
        
        # Иннициализация CPU чтобы избежать первого замера 0
        self._process.cpu_percent()

    def update(self, inference_ms=None):
        """
        Обновляет показатели FPS, ресурсов и прикладных метрик.
        Values can be passed directly for atomic updates.
        """
        curr_time = time.perf_counter()
        delta = curr_time - self.prev_time
        if delta > 0:
            # Сглаживание FPS (EMA)
            instant_fps = 1.0 / delta
            self.fps = 0.9 * self.fps + 0.1 * instant_fps
        self.prev_time = curr_time

        # Прикладные метрики и расчет нагрузки
        if inference_ms is not None:
            self.inference_ms = 0.8 * self.inference_ms + 0.2 * inference_ms
            
            # Расчет GPU load как отношение времени инференса к бюджету кадра
            if self.fps > 0:
                budget_ms = 1000.0 / self.fps
                # Нагрузка в % (не более 100)
                instant_load = (self.inference_ms / budget_ms) * 100.0
                self.gpu_load = min(100.0, instant_load)

        # Системные ресурсы обновляем раз в секунду
        if curr_time - self._last_sys_update > 1.0:
            try:
                # CPU конкретного процесса
                self.cpu_usage = self._process.cpu_percent() / psutil.cpu_count()
                
                # RAM конкретного процесса в ГБ
                process_mem = self._process.memory_info().rss
                self.ram_usage = process_mem / (1024 ** 3)
                
                # Лимит RAM
                virtual_mem = psutil.virtual_memory()
                self.ram_total = virtual_mem.total / (1024 ** 3)
                self.ram_percent = (process_mem / virtual_mem.total) * 100
                
                # Статус MPS
                self.mps_status = self._get_mps_status()
                
            except Exception as e:
                logger.debug(f"Ошибка обновления метрик: {e}")
            self._last_sys_update = curr_time

    def _get_mps_status(self):
        """Проверяет доступность и использование MPS (Metal Performance Shaders)."""
        if not HAS_TORCH:
            return "N/A"
        try:
            if torch.backends.mps.is_available():
                return "ACTIVE" if torch.backends.mps.is_built() else "READY"
        except Exception:
            pass
        return "OFF"

    def get_stats(self):
        """Возвращает словарь с текущими показателями."""
        return {
            'fps': self.fps,
            'cpu': self.cpu_usage,
            'ram_gb': self.ram_usage,
            'ram_total': self.ram_total,
            'ram_percent': self.ram_percent,
            'gpu_status': self.mps_status,
            'inference_ms': self.inference_ms,
            'gpu_load': self.gpu_load
        }
