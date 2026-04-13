from dataclasses import dataclass


@dataclass
class EventsParams:
    """Параметры анализа событий (консультации, группы)."""

    proximity_threshold_px: int = 250
    """Радиус объединения людей в группу (пиксели)."""

    min_group_size: int = 2
    """Минимальное кол-во людей для формирования группы."""

    consultation_required_roles: bool = True
    """Требовать наличие и клиента, и персонала для события консультации."""
