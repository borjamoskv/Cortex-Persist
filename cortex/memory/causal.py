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


@dataclass(slots=True)
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

    def impact_chain(self, engram_id: str, max_depth: int = 5) -> list[str]:
        """Trace the full downstream impact chain (BFS).

        Returns list of engram IDs that depend on this one.
        """
        visited: set[str] = set()
        queue = [engram_id]
        chain: list[str] = []

        for _ in range(max_depth):
            if not queue:
                break
            queue = self._process_impact_queue(queue, visited, chain, engram_id)

        return chain

    def _process_impact_queue(
        self, queue: list[str], visited: set[str], chain: list[str], start_id: str
    ) -> list[str]:
        next_queue: list[str] = []
        for eid in queue:
            if eid in visited:
                continue
            visited.add(eid)
            if eid != start_id:
                chain.append(eid)
            next_queue.extend(
                link.effect_id
                for link in self._forward.get(eid, [])
                if link.effect_id not in visited
            )
        return next_queue

    def root_causes(self, engram_id: str, max_depth: int = 5) -> list[str]:
        """Trace backward to find all root causes (no incoming edges)."""
        visited: set[str] = set()
        queue = [engram_id]
        roots: list[str] = []

        for _ in range(max_depth):
            if not queue:
                break
            queue = self._process_root_queue(queue, visited, roots, engram_id)

        return roots

    def _process_root_queue(
        self, queue: list[str], visited: set[str], roots: list[str], start_id: str
    ) -> list[str]:
        next_queue: list[str] = []
        for eid in queue:
            if eid in visited:
                continue
            visited.add(eid)
            causes = self._backward.get(eid, [])
            if not causes and eid != start_id:
                roots.append(eid)
            next_queue.extend(link.cause_id for link in causes if link.cause_id not in visited)
        return next_queue

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
