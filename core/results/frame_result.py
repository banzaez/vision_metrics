from dataclasses import dataclass
from typing import Optional


@dataclass
class FrameResult:
    success: bool
    frame_id: int
    detections: Optional[list] = None
    error: Optional[str] = None
    processing_time_ms: float = 0

    @staticmethod
    def ok(frame_id: int, detections: list, time_ms: float) -> 'FrameResult':
        return FrameResult(True, frame_id, detections, None, time_ms)

    @staticmethod
    def error(frame_id: int, error_msg: str) -> 'FrameResult':
        return FrameResult(False, frame_id, None, error_msg, 0)


@dataclass
class PipelineResult:
    success: bool
    frames_processed: int = 0
    errors: list = None

    @staticmethod
    def ok(frames: int) -> 'PipelineResult':
        return PipelineResult(True, frames, [])

    @staticmethod
    def failed(errors: list) -> 'PipelineResult':
        return PipelineResult(False, 0, errors)