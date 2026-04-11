from dataclasses import dataclass
from enum import Enum

class YOLOModel(str, Enum):
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
    S = 640
    M = 960
    L = 1280
    XL = 1536
    XXL = 1920


@dataclass
class YOLOParams:
    """Параметры модели детекции и сегментации (YOLO)."""

    path_to_models: str = "./data/models/"

    # Имя файла весов модели YOLO (.pt)
    weights: str = path_to_models + YOLOModel.YOLO26S.value

    # Размер изображения для инференса (640, 960, 1280)
    imgsz: int = YOLOImageSize.M.value

    # Порог уверенности: детекции ниже этого значения игнорируются для конечного вывода.
    conf_threshold: float = 0.30

    # Порог Intersection Over Union для подавления дублирующих боксов
    iou_threshold: float = 0.5

    # Классово-независимая фильтрация (NMS): удаляет пересекающиеся боксы разных классов
    agnostic_nms: bool = False
    
    # Использовать высокоточные маски (более медленно, но точнее) ДЛЯ МОДЕЛЕЙ С ПРИПИСКОЙ _SEG
    retina_masks: bool = False
