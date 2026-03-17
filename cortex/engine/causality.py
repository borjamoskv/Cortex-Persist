from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class EpistemicStatus(str, Enum):
    CONJECTURE = "conjecture"
    TEST_PASSED = "test_passed"
    REFUTED = "refuted"
    OBSOLETE = "obsolete"


@dataclass
class LedgerEvent:
    event_id: str
    parent_ids: list[str]
    status: EpistemicStatus
    trust_score: float
    created_at: str
    last_revalidated_at: Optional[str] = None
    tainted: bool = False


class CausalGraph:
    def __init__(self):
        self._events: Dict[str, LedgerEvent] = {}
        self._children: Dict[str, List[str]] = {}

    def get_event(self, event_id: str) -> LedgerEvent:
        return self._events[event_id]

    def add_event(self, event: LedgerEvent):
        self._events[event.event_id] = event
        if event.event_id not in self._children:
            self._children[event.event_id] = []
            
        for parent_id in event.parent_ids:
            if parent_id not in self._children:
                self._children[parent_id] = []
            self._children[parent_id].append(event.event_id)

    def get_descendants(self, node_id: str) -> List[str]:
        return self._children.get(node_id, [])

    def __getitem__(self, node_id: str) -> LedgerEvent:
        return self.get_event(node_id)


def propagate_refutation(graph: CausalGraph, refuted_event_id: str, decay: float = 0.35) -> None:
    queue = [(refuted_event_id, 0)]
    visited = set()

    while queue:
        node_id, depth = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)

        try:
            event = graph[node_id]
        except KeyError:
            continue

        if depth == 0:
            event.status = EpistemicStatus.REFUTED
            event.trust_score = 0.0
        else:
            event.trust_score = max(0.0, event.trust_score * (1.0 - decay / max(depth, 1)))
            event.tainted = True

        for child_id in graph.get_descendants(node_id):
            queue.append((child_id, depth + 1))
