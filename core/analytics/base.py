from abc import ABC, abstractmethod


class TrackProcessorBase(ABC):
    @abstractmethod
    def process_track(self, track_id: int, frame_data: dict) -> dict:
        pass
    
    @abstractmethod
    def cleanup(self, track_id: int) -> None:
        pass