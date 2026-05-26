"""CORTEX v6+ — Causal Memory Graph (do-calculus chains).

Strategy #6: Don't just store WHAT happened — store WHY.
Each engram carries a causal chain enabling:
- Contrafactual reasoning: "What if we reverted this?"
- Zombie decision detection: if the cause no longer exists,
  the decision may be obsolete
- Impact analysis: "What depends on this fact?"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("cortex.memory.causal")


@dataclass()
class CausalLink:
    """A directed causal relationship between two engrams."""

    cause_id: str
    effect_id: str
    relation: str = "caused"  # caused, enabled, prevented, required
    strength: float = 1.0  # 0.0 = weak, 1.0 = strong
    description: str = ""

    @property
    def is_strong(self) -> bool:
        return self.strength >= 0.7


class CausalGraph:
    """Directed graph of causal relationships between engrams.

    Enables:
    - Forward tracing: "What did this decision cause?"
    - Backward tracing: "Why was this decision made?"
    - Zombie detection: "Is the root cause still valid?"
    - Impact analysis: "What breaks if I remove this?"
    """

    def __init__(self):
        self._forward: dict[str, list[CausalLink]] = {}  # cause → effects
        self._backward: dict[str, list[CausalLink]] = {}  # effect → causes

    def add_link(self, link: CausalLink) -> None:
        """Add a causal relationship."""
        self._forward.setdefault(link.cause_id, []).append(link)
        self._backward.setdefault(link.effect_id, []).append(link)
        logger.debug(
            "Causal link: %s -[%s]-> %s",
            link.cause_id,
            link.relation,
            link.effect_id,
        )

    def effects_of(self, engram_id: str) -> list[CausalLink]:
        """What did this engram cause? (forward trace)"""
        return self._forward.get(engram_id, [])

    def causes_of(self, engram_id: str) -> list[CausalLink]:
        """Why does this engram exist? (backward trace)"""
        return self._backward.get(engram_id, [])

    def _traverse_causal_graph(
        self,
        start_id: str,
        forward: bool = True,
        max_depth: int = 5,
        collect_roots_only: bool = False,
    ) -> list[str]:
        """Unified BFS traversal of the causal graph."""
        visited: set[str] = set()
        queue = [start_id]
        result: list[str] = []

        graph = self._forward if forward else self._backward

        for _ in range(max_depth):
            if not queue:
                break
            next_queue: list[str] = []
            for eid in queue:
                if eid in visited:
                    continue
                visited.add(eid)

                if eid != start_id:
                    if collect_roots_only:
                        if not self._backward.get(eid):
                            result.append(eid)
                    else:
                        result.append(eid)

                neighbors = graph.get(eid, [])
                for link in neighbors:
                    nxt = link.effect_id if forward else link.cause_id
                    if nxt not in visited:
                        next_queue.append(nxt)
            queue = next_queue

        return result

    def impact_chain(self, engram_id: str, max_depth: int = 5) -> list[str]:
        """Trace the full downstream impact chain (BFS).

        Returns list of engram IDs that depend on this one.
        """
        return self._traverse_causal_graph(
            engram_id, forward=True, max_depth=max_depth, collect_roots_only=False
        )

    def root_causes(self, engram_id: str, max_depth: int = 5) -> list[str]:
        """Trace backward to find all root causes (no incoming edges)."""
        return self._traverse_causal_graph(
            engram_id, forward=False, max_depth=max_depth, collect_roots_only=True
        )

    def find_zombies(self, alive_ids: set[str]) -> list[str]:
        """Find decisions whose root causes no longer exist.

        A "zombie decision" is one where ALL root causes have
        been pruned/deprecated but the decision persists.
        """
        zombies: list[str] = []
        for eid in self._backward:
            if eid not in alive_ids:
                continue
            roots = self.root_causes(eid)
            if roots and all(r not in alive_ids for r in roots):
                zombies.append(eid)
        return zombies

    @property
    def node_count(self) -> int:
        all_ids = set(self._forward.keys()) | set(self._backward.keys())
        return len(all_ids)

    @property
    def edge_count(self) -> int:
        return sum(len(links) for links in self._forward.values())
