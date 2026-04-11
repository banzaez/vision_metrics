from abc import ABC, abstractmethod
import cv2
import numpy as np
import os


class VideoSource(ABC):
    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray]:
        pass
    
    @abstractmethod
    def get_properties(self) -> dict:
        pass
    
    @abstractmethod
    def release(self) -> None:
        pass
    
    @property
    @abstractmethod
    def is_opened(self) -> bool:
        pass


class FileVideoSource(VideoSource):
    def __init__(self, file_path: str):
        self._cap = cv2.VideoCapture(file_path)
        self._file_path = file_path
        
    def read(self) -> tuple[bool, np.ndarray]:
        return self._cap.read()
    
    def get_properties(self) -> dict:
        return {
            "fps": self._cap.get(cv2.CAP_PROP_FPS),
            "frame_count": int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "source": self._file_path
        }
    
    def release(self) -> None:
        self._cap.release()
    
    @property
    def is_opened(self) -> bool:
        return self._cap.isOpened()


class StreamVideoSource(VideoSource):
    def __init__(self, url: str):
        self._cap = cv2.VideoCapture(url)
        self._url = url
        
    def read(self) -> tuple[bool, np.ndarray]:
        return self._cap.read()
    
    def get_properties(self) -> dict:
        return {
            "fps": self._cap.get(cv2.CAP_PROP_FPS),
            "frame_count": 0,
            "width": int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "source": self._url
        }
    
    def release(self) -> None:
        self._cap.release()
    
    @property
    def is_opened(self) -> bool:
        return self._cap.isOpened()


def create_video_source(source) -> VideoSource:
    if isinstance(source, str) and any(source.startswith(p) for p in ["rtsp://", "http://", "https://"]):
        return StreamVideoSource(source)
    if isinstance(source, str) and os.path.isfile(source):
        return FileVideoSource(source)
    return FileVideoSource(source)