from collections import deque
from typing import Any
from cortex.engine.causality_models import LedgerEvent, EpistemicStatus

class CausalGraph:
    def __init__(self) -> None:
        self._events: dict[str, LedgerEvent] = {}
        self._children: dict[str, list[str]] = {}

    def get_event(self, event_id: str) -> LedgerEvent:
        return self._events[event_id]

    def add_event(self, event: LedgerEvent) -> None:
        self._events[event.event_id] = event
        self._children.setdefault(event.event_id, [])
        for parent_id in event.parent_ids:
            self._children.setdefault(parent_id, []).append(event.event_id)

    def get_descendants(self, node_id: str) -> list[str]:
        return self._children.get(node_id, [])

    def __getitem__(self, node_id: str) -> LedgerEvent:
        return self.get_event(node_id)


def propagate_refutation(graph: CausalGraph, refuted_event_id: str, decay: float = 0.35) -> None:
    queue = deque([(refuted_event_id, 0)])
    visited: set[str] = set()

    while queue:
        node_id, depth = queue.popleft()
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
