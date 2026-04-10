import cv2
import threading
import queue
import time

class VideoStream:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.q = queue.Queue(maxsize=32)
        self.stopped = False
        self.seek_request = None
        self.lock = threading.Lock()
        
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        
    def start(self):
        # Start reading frames in a background thread
        self.thread.start()
        return self

    def update(self):
        while True:
            if self.stopped:
                return
                
            with self.lock:
                req = self.seek_request
                self.seek_request = None
                
            if req is not None:
                # Переходим на перемотку по миллисекундам (более надежно для файлов)
                current_ms = self.stream.get(cv2.CAP_PROP_POS_MSEC)
                new_ms = max(0, current_ms + (req * 1000.0))
                self.stream.set(cv2.CAP_PROP_POS_MSEC, new_ms)
                
                print(f"[Stream] Перемотка: {current_ms/1000:.1f}s -> {new_ms/1000:.1f}s")
                
                # "Прогрев" декодера
                for _ in range(5):
                    self.stream.grab()
                while not self.q.empty():
                    try:
                        self.q.get_nowait()
                    except queue.Empty:
                        break
                        
            try:
                ret, frame = self.stream.read()
                if not ret:
                    self.stop()
                    return
                self.q.put_nowait(frame)
            except queue.Full:
                # Sleep a bit to prevent high CPU usage when queue is full
                time.sleep(0.01)

    def read(self):
        try:
            return True, self.q.get_nowait()
        except queue.Empty:
            return False, None

    def seek(self, seconds):
        # Передаем запрос на перемотку в фоновый поток (во избежание крэша ffmpeg)
        with self.lock:
            self.seek_request = seconds

    def stop(self):
        self.stopped = True
        if self.stream.isOpened():
            self.stream.release()
