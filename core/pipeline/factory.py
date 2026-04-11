import os
import logging
import config
from core.pipeline.orchestrator import DetectorTracker
from core.analytics.data_logger import JSONDataLogger
from utils.filename_parser import parse_nvr_filename

logger = logging.getLogger(__name__)


class PipelineFactory:
    @staticmethod
    def create_detector_tracker(video_source, camera_id_override=None):
        """
        Фабрика для создания DetectorTracker с правильной инициализацией.

        Args:
            video_source: Путь к видеофайлу или URL стрима
            camera_id_override: Опциональный override для camera_id

        Returns:
            Tuple[DetectorTracker, dict]: detector и метаданные видео
        """
        cfg_yolo = config.settings.yolo
        cfg_perf = config.settings.system.perf

        filename = os.path.basename(video_source) if isinstance(video_source, str) else "stream"
        nvr_meta = parse_nvr_filename(filename)
        camera_id = camera_id_override or nvr_meta.get("camera_id", "unknown")

        detector = DetectorTracker(
            model_path=cfg_yolo.weights,
            camera_id=camera_id,
            device=cfg_perf.device,
            half=cfg_perf.half,
        )

        logger.info(f"DetectorTracker создан для камеры: {camera_id}")
        return detector, nvr_meta

    @staticmethod
    def create_data_logger(video_source):
        """
        Фабрика для создания и настройки логгера.

        Args:
            video_source: Путь к видеофайлу или URL стрима

        Returns:
            Tuple[JSONDataLogger, dict]: логгер и метаданные видео
        """
        import cv2

        data_logger = JSONDataLogger(output_path="")
        data_logger.setup_from_video(video_source)

        filename = os.path.basename(video_source) if isinstance(video_source, str) else "stream"
        nvr_meta = parse_nvr_filename(filename)

        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            logger.warning(f"Не удалось получить метаданные видео: {video_source}")
            return data_logger, nvr_meta

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            camera_id = nvr_meta.get("camera_id", "unknown")

            meta = {
                "camera_id": camera_id,
                "filename": filename,
                "fps": float(fps) if fps > 0 else 25.0,
                "width": width,
                "height": height,
                "total_frames": total_frames
            }
            meta.update(nvr_meta)

            data_logger.metadata = meta
            data_logger.open()
        finally:
            cap.release()

        return data_logger, meta

    @staticmethod
    def configure_detector(detector, fps):
        """
        Конфигурирует detector после инициализации.

        Args:
            detector: Экземпляр DetectorTracker
            fps: FPS видео
        """
        detector.fps = fps
        if hasattr(detector, 'track_processor'):
            cfg_analytics = config.settings.analytics
            if hasattr(detector.track_processor, 'camera_id'):
                detector.track_processor.camera_id = detector.camera_id