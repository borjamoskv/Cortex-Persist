from typing import Optional
from dataclasses import dataclass
from enum import Enum

import aiosqlite


class EpistemicStatus(str, Enum):
    CONJECTURE = "conjecture"
    TEST_PASSED = "test_passed"
    REFUTED = "refuted"
    OBSOLETE = "obsolete"


EDGE_DERIVED_FROM = "derived_from"
EDGE_TRIGGERED_BY = "triggered_by"
EDGE_UPDATED_FROM = "updated_from"
EDGE_TAINTED_BY = "tainted_by"


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
        self._events: dict[str, LedgerEvent] = {}
        self._children: dict[str, list[str]] = {}

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

    def get_descendants(self, node_id: str) -> list[str]:
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
            if child_id not in visited:
                queue.append((child_id, depth + 1))

class AsyncCausalGraph:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def propagate_taint(self, fact_id: int, tenant_id: str) -> None:
        """Propagate taint (C1 confidence + tainted flag) to all children in the DAG."""
        # This is a database-backed propagation
        queue = [(fact_id, 0)]
        visited = {fact_id}

        while queue:
            current_id, depth = queue.pop(0)
            
            # Update current fact if it's not the root (root is updated by caller usually, but let's be safe)
            if depth > 0:
                # Update confidence and mark as tainted
                # We use a direct SQL update for performance within the transaction
                await self.conn.execute(
                    "UPDATE facts_meta SET confidence = 'C1', tainted = 1 WHERE id = ?",
                    (current_id,)
                )
            
            # Find children
            async with self.conn.execute(
                "SELECT id FROM facts WHERE parent_decision_id = ? AND tenant_id = ?",
                (current_id, tenant_id)
            ) as cursor:
                async for row in cursor:
                    child_id = row[0]
                    if child_id not in visited:
                        visited.add(child_id)
                        queue.append((child_id, depth + 1))

    async def calculate_blast_radius(self, fact_id: int, tenant_id: str) -> int:
        """Calculate the number of dependent facts in the causal DAG."""
        count = 0
        queue = [fact_id]
        visited = {fact_id}

        while queue:
            current_id = queue.pop(0)
            async with self.conn.execute(
                "SELECT id FROM facts WHERE parent_decision_id = ? AND tenant_id = ?",
                (current_id, tenant_id)
            ) as cursor:
                async for row in cursor:
                    child_id = row[0]
                    if child_id not in visited:
                        visited.add(child_id)
                        queue.append(child_id)
                        count += 1
        return count
