import json
import os
import logging

logger = logging.getLogger(__name__)

class JSONDataLogger:
    """
    Класс для высокопроизводительной потоковой записи результатов трекинга в JSON.
    Обеспечивает иерархическую структуру root -> frames -> objects.
    """
    def __init__(self, output_path=None, metadata=None):
        self.output_path = output_path
        self.metadata = metadata or {}
        self.file = None
        self._first_frame = True

    def setup_from_video(self, video_path):
        """
        Автоматически настраивает путь сохранения на основе пути к видео.
        Добавляет префикс json_ и расширение .json.
        """
        import os
        filename = os.path.basename(video_path)
        # Убираем префикс json_, просто меняем расширение
        json_name = os.path.splitext(filename)[0] + ".json"
        self.output_path = os.path.join("data", "results", json_name)
        return self.output_path
        
    def open(self):
        """Инициализирует файл и записывает заголовок с метаданными."""
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            self.file = open(self.output_path, "w", encoding="utf-8")
            
            # Формируем стартовую структуру JSON: {"metadata": {...}, "frames": [
            header = {
                "metadata": self.metadata,
                "frames": []
            }
            # Сериализуем и обрезаем закрывающие скобки "]}" для потоковой записи ведомых элементов
            header_str = json.dumps(header, ensure_ascii=False)[:-2]
            self.file.write(header_str + "\n")
            self._first_frame = True
            logger.info(f"JSON Logger открыт: {self.output_path}")
        except Exception as e:
            logger.error(f"Ошибка открытия логгера: {e}")
            self.file = None

    def log_frame(self, frame_id, objects, flush=False):
        """Записывает данные одного кадра в массив frames."""
        if not self.file or not objects:
            return
            
        try:
            frame_entry = {
                "frame_id": frame_id,
                "objects": objects
            }
            
            # Формируем строку элемента массива с правильной пунктуацией
            prefix = "    " if self._first_frame else ",\n    "
            self.file.write(prefix + json.dumps(frame_entry, ensure_ascii=False))
            self._first_frame = False
            
            if flush:
                self.file.flush()
        except Exception as e:
            logger.error(f"Ошибка записи кадра {frame_id} в лог: {e}")

    def close(self):
        """Закрывает JSON структуру и файл."""
        if self.file:
            try:
                self.file.write("\n  ]\n}")
                self.file.close()
                logger.info(f"JSON Logger успешно сохранен: {self.output_path}")
            except Exception as e:
                logger.error(f"Ошибка при закрытии логгера: {e}")
            finally:
                self.file = None
