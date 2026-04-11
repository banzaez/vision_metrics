from dataclasses import dataclass
from enum import Enum


class YOLOModel(str, Enum):
    """Доступные модели YOLO для детекции и сегментации."""

    YOLO26N_SEG = "yolo26n-seg.pt"
    YOLO26N = "yolo26n.pt"
    YOLO26S_SEG = "yolo26s-seg.pt"
    YOLO26S = "yolo26s.pt"
    YOLO26M_SEG = "yolo26m-seg.pt"
    YOLO26M = "yolo26m.pt"
    YOLO26L_SEG = "yolo26l-seg.pt"
    YOLO26L = "yolo26l.pt"
    YOLO26X_SEG = "yolo26x-seg.pt"
    YOLO26X = "yolo26x.pt"


class YOLOImageSize(int, Enum):
    """Размеры изображения для инференса YOLO."""

    S = 640
    M = 960
    L = 1280
    XL = 1536
    XXL = 1920


@dataclass
class YOLOParams:
    """Параметры модели детекции и сегментации (YOLO)."""

    path_to_models: str = "./data/models/"
    """Путь к директории с весами моделей."""

    weights: str = path_to_models + YOLOModel.YOLO26S.value
    """Имя файла весов модели YOLO (.pt)."""

    imgsz: int = YOLOImageSize.M.value
    """Размер изображения для инференса (640, 960, 1280, ...)."""

    conf_threshold: float = 0.30
    """Порог уверенности: детекции ниже этого значения игнорируются."""

    iou_threshold: float = 0.5
    """Порог IoU для подавления дублирующих боксов (NMS)."""

    agnostic_nms: bool = False
    """Классово-независимая фильтрация NMS: удаляет пересекающиеся боксы разных классов."""

    retina_masks: bool = False
    """Высокоточные маски (медленнее, но точнее). Только для моделей _SEG."""
