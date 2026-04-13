from .app_config import AppConfig
from .sections.system import SystemConfig, PerformanceConfig, UIConfig
from .sections.yolo import YOLOParams, YOLOModel, YOLOImageSize
from .sections.tracker import TrackerConfig, TrackerType, ReIDModel
from .sections.reid import CustomReIDConfig

# =============================================================================
# ГЛАВНЫЙ ФАЙЛ НАСТРОЕК (VISION METRICS)
# =============================================================================
# Этот файл является основной точкой входа для настройки системы.
# Здесь вы можете быстро переключать модели, менять пороги детекции и 
# настраивать производительность без необходимости искать классы в коде.
#
# КЛАССЫ И ТИПЫ: Все определения (dataclasses и enums) хранятся в 
# папке config/sections/, чтобы этот файл оставался чистым и понятным.
# =============================================================================

settings = AppConfig(
    # --- СИСТЕМНЫЕ НАСТРОЙКИ (ПРОИЗВОДИТЕЛЬНОСТЬ И ИНТЕРФЕЙС) ---
    system=SystemConfig(
        perf=PerformanceConfig(
            # Вычислительное устройство: 'cuda', 'mps' (Apple Silicon), 'cpu'
            # Также можно использовать 'auto' для автоматического определения.
            device='auto', 
            
            # Режим половинной точности (FP16). Рекомендуется для ускорения.
            half=True,
            
            # Размер пакета (batch size). 1 - для реального времени.
            batch_size=1,
            
            # Требуемый FPS. Используется, если не удалось определить автоматически.
            frame_rate=25,
            
            # Пропуск кадров. 3 означает обработку каждого 3-го кадра.
            frame_interval=3,
            
            # Потоки для декодирования видео (OpenCV).
            opencv_threads=4
        ),
        ui=UIConfig(
            # Перемотка видео (в кадрах).
            step_frames=125,
            
            # Панель мониторинга ресурсов (FPS, CPU, RAM).
            show_monitoring=True
        ),
        # Пути к видеофайлам или RTSP-стримы.
        video_sources=[
            './data/videos/Camera_01_10.12.0.35_10.12.0.235_20260401113050_20260401113550_3084159.mp4'
        ]
    ),

    # --- НАСТРОЙКИ МОДЕЛИ ДЕТЕКЦИИ (YOLO) ---
    yolo=YOLOParams(
        # Папка с весами моделей .pt
        path_to_models="./data/models/",
        
        # Файл весов YOLO.
        weights="./data/models/" + YOLOModel.YOLO26S.value,
        
        # Размер изображения для инференса (S=640, M=960, L=1280, XL=1536, XXL=1920).
        imgsz=YOLOImageSize.M.value,
        
        # Порог уверенности (Confidence Threshold).
        conf_threshold=0.30,
        
        # Порог IoU (NMS).
        iou_threshold=0.5,
        
        # Агностический NMS.
        agnostic_nms=False,
        
        # Retina-маски (для сегментации).
        retina_masks=False
    ),

    # --- НАСТРОЙКИ ТРЕКЕРА И RE-ID (ОТСЛЕЖИВАНИЕ) ---
    tracker=TrackerConfig(
        # Алгоритм трекинга (HYBRIDSORT - рекомендуемый).
        type=TrackerType.HYBRIDSORT,
        
        # Использовать Re-ID (внешний вид объектов).
        with_reid=True,
        
        # Модель Re-ID (OSNET_X1_0 - стандарт).
        reid_model=ReIDModel.OSNET_X1_0,
        
        # Индексы классов для отслеживания (0 - person).
        classes=[0],
        
        # Кастомная сшивка треков (CustomReIDStitcher).
        custom_reid=CustomReIDConfig(
            # Включить/выключить кастомную сшивку треков.
            enabled=False,
            # Порог похожести векторов (0.0 - 1.0).
            threshold=0.6,
            # Размер галереи объектов.
            gallery_size=100,
            # Сглаживание EMA.
            ema_alpha=0.6,
            # Интервал обновления статистики в UI.
            stats_callback_interval=15
        )
    )
)

# Загрузка динамических данных (ROI, зоны)
settings.load()
