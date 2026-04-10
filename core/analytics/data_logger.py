import json
import os
import logging

logger = logging.getLogger(__name__)

class JSONDataLogger:
    """
    Класс для высокопроизводительной потоковой записи резуль��атов трекинга в JSONL.
    Каждая строка — отдельный валидный JSON-объект. Корректный при краше процесса.
    """
    def __init__(self, output_path=None, metadata=None):
        self.output_path = output_path
        self.metadata = metadata or {}
        self.file = None
        self._first_write = True

    def setup_from_video(self, video_path):
        """
        Автоматически настраивает путь сохранения на основе пути к видео.
        """
        import os
        filename = os.path.basename(video_path)
        json_name = os.path.splitext(filename)[0] + ".jsonl"
        self.output_path = os.path.join("data", "results", json_name)
        return self.output_path
        
    def open(self):
        """Инициализирует файл и записывает метаданные."""
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            self.file = open(self.output_path, "w", encoding="utf-8")
            
            self.file.write(json.dumps({"type": "metadata", "data": self.metadata}, ensure_ascii=False) + "\n")
            self._first_write = True
            logger.info(f"JSONL Logger открыт: {self.output_path}")
        except Exception as e:
            logger.error(f"Ошибка открытия логгера: {e}")
            if self.file:
                self.file.close()
            self.file = None

    def log_frame(self, frame_id, objects, flush=False):
        """Записывает данные одного кадра (одна строка = один JSON)."""
        if not self.file or not objects:
            return
            
        try:
            frame_entry = {
                "type": "frame",
                "frame_id": frame_id,
                "objects": objects
            }
            self.file.write(json.dumps(frame_entry, ensure_ascii=False) + "\n")
            
            if flush:
                self.file.flush()
        except Exception as e:
            logger.error(f"Ошибка записи кадра {frame_id} в лог: {e}")

    def close(self):
        """Закрывает файл."""
        if self.file:
            try:
                self.file.write(json.dumps({"type": "eof"}, ensure_ascii=False) + "\n")
                self.file.close()
                logger.info(f"JSONL Logger сохранен: {self.output_path}")
            except Exception as e:
                logger.error(f"Ошибка при закрытии логгера: {e}")
            finally:
                self.file = None
