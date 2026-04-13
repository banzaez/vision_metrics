import logging
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple
from core.tracking.person_data import PersonData
from config.sections.events import EventsParams

logger = logging.getLogger(__name__)


@dataclass
class ProximityGroup:
    """Объект группы людей, находящихся рядом."""
    group_id: str
    track_ids: List[int]
    staff_ids: List[int]
    client_ids: List[int]
    bbox: Tuple[int, int, int, int]
    center: Tuple[float, float]

    @property
    def is_consultation(self) -> bool:
        """Групповое событие считается консультацией, если в нем есть персонал и клиенты."""
        return len(self.staff_ids) > 0 and len(self.client_ids) > 0

class EventAnalyzer:
    """
    Класс для анализа групповых взаимодействий на основе объектов PersonData.
    """

    def __init__(self, config: EventsParams = None):
        self.config = config or EventsParams()

    def analyze(self, persons: List[PersonData], frame_id: int) -> List[ProximityGroup]:
        """
        Группирует людей и находит взаимодействия.
        """
        if len(persons) < 2:
            return []

        # 1. Строим граф связей
        adj = self._build_adjacency_list(persons)

        # 2. Группируем ID
        groups_ids = self._find_connected_components(adj, [p.track_id for p in persons])

        # 3. Формируем группы
        proximity_groups = []
        person_map = {p.track_id: p for p in persons}

        for i, group_track_ids in enumerate(groups_ids):
            if len(group_track_ids) < self.config.min_group_size:
                continue
            
            # Разделяем на роли внутри группы
            staff = [tid for tid in group_track_ids if person_map[tid].is_staff]
            clients = [tid for tid in group_track_ids if not person_map[tid].is_staff]
            
            # Фильтр: группа эвента только тогда, когда есть и сотрудник, и хотя бы 1 покупатель (если включено в конфиге)
            if self.config.consultation_required_roles:
                if len(staff) == 0 or len(clients) == 0:
                    continue

            group_bbox = self._calculate_group_bbox([person_map[tid].last_bbox for tid in group_track_ids])
            cx = (group_bbox[0] + group_bbox[2]) / 2
            cy = (group_bbox[1] + group_bbox[3]) / 2
            
            proximity_groups.append(ProximityGroup(
                group_id=f"group_{frame_id}_{i}",
                track_ids=group_track_ids,
                staff_ids=staff,
                client_ids=clients,
                bbox=group_bbox,
                center=(cx, cy)
            ))
        
        return proximity_groups

    def _build_adjacency_list(self, persons: List[PersonData]) -> Dict[int, List[int]]:
        adj = {p.track_id: [] for p in persons}
        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                p1, p2 = persons[i], persons[j]
                
                # Расстояние между центрами
                dist = math.sqrt((p1.center[0] - p2.center[0])**2 + (p1.center[1] - p2.center[1])**2)
                
                if dist < self.config.proximity_threshold_px:
                    adj[p1.track_id].append(p2.track_id)
                    adj[p2.track_id].append(p1.track_id)
        return adj

    def _find_connected_components(self, adj: Dict[int, List[int]], all_ids: List[int]) -> List[List[int]]:
        """Находит группы людей (связные компоненты) в графе."""
        visited = set()
        components = []

        for node_id in all_ids:
            if node_id not in visited:
                component = []
                stack = [node_id]
                visited.add(node_id)
                
                while stack:
                    curr = stack.pop()
                    component.append(curr)
                    for neighbor in adj.get(curr, []):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            stack.append(neighbor)
                
                components.append(component)
        
        return components

    def _calculate_distance(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """Расчет расстояния между центрами bbox."""
        c1 = ((bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2)
        c2 = ((bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2)
        return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

    def _calculate_group_bbox(self, bboxes: List[Tuple]) -> Tuple[int, int, int, int]:
        """Рассчитывает охватывающий прямоугольник для списка bbox."""
        x1 = min(b[0] for b in bboxes)
        y1 = min(b[1] for b in bboxes)
        x2 = max(b[2] for b in bboxes)
        y2 = max(b[3] for b in bboxes)
        return (int(x1), int(y1), int(x2), int(y2))
