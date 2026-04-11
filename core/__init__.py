from .pipeline.orchestrator import DetectorTracker
from .detection.yolo_detector import YOLODetector
from .tracking.tracking_service import TrackingService

# Aliases for cleaner API
AnalyticsPipeline = DetectorTracker

__all__ = [
    'DetectorTracker',
    'YOLODetector',
    'TrackingService',
    'AnalyticsPipeline',
]
