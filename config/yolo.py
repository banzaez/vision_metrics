from dataclasses import dataclass


@dataclass
class YOLOParams:
    """Параметры модели детекции и сегментации (YOLO)."""

    # Имя файла весов модели YOLO (.pt)
    weights: str = "yolo26m-seg.pt"
    # Размер изображения для инференса (кратный 32)
    imgsz: int = 640
    # Порог уверенности: детекции ниже этого значения игнорируются для конечного вывода.
    conf_threshold: float = 0.10
    # Порог Intersection Over Union для подавления дублирующих боксов
    iou_threshold: float = 0.5
    # Классово-независимая фильтрация (NMS): удаляет пересекающиеся боксы разных классов
    agnostic_nms: bool = True
    # Использовать высокоточные маски (более медленно, но точнее)
    retina_masks: bool = True
