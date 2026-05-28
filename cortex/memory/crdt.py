"""CORTEX v6+ — CRDT Memory Merge (Multi-Agent Eventual Consistency).

Strategy #7: When multiple agents work in parallel (LEGIØN-1),
each accumulates independent memories. CRDTs enable conflict-free
merge without coordination:

- G-Counter for access counts (only grows)
- LWW-Register for content (last-write-wins with timestamp)
- OR-Set for tags (union of all tags)

No framework has this for agent memory. This is the killer feature.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("cortex.memory.crdt")


@dataclass
class GCounter:
    """Grow-only counter CRDT. Each agent has its own slot."""

    _counts: dict[str, int] = field(default_factory=dict)

    def increment(self, agent_id: str, amount: int = 1) -> None:
        self._counts[agent_id] = self._counts.get(agent_id, 0) + amount

    @property
    def value(self) -> int:
        return sum(self._counts.values())

    def merge(self, other: GCounter) -> GCounter:
        """Merge two counters by taking max per agent."""
        merged = GCounter()
        all_agents = set(self._counts.keys()) | set(other._counts.keys())
        for agent in all_agents:
            merged._counts[agent] = max(
                self._counts.get(agent, 0),
                other._counts.get(agent, 0),
            )
        return merged


@dataclass
class LWWRegister:
    """Last-Writer-Wins Register CRDT with timestamp."""

    value: str = ""
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""

    def update(self, new_value: str, agent_id: str) -> None:
        now = time.time()
        if now >= self.timestamp:
            self.value = new_value
            self.timestamp = now
            self.agent_id = agent_id

    def merge(self, other: LWWRegister) -> LWWRegister:
        """Merge by keeping the latest write."""
        if other.timestamp > self.timestamp:
            return LWWRegister(
                value=other.value,
                timestamp=other.timestamp,
                agent_id=other.agent_id,
            )
        return LWWRegister(
            value=self.value,
            timestamp=self.timestamp,
            agent_id=self.agent_id,
        )


@dataclass
class ORSet:
    """Observed-Remove Set CRDT. Union semantics — both sides win."""

    _elements: dict[str, float] = field(default_factory=dict)

    def add(self, element: str) -> None:
        self._elements[element] = time.time()

    def remove(self, element: str) -> None:
        self._elements.pop(element, None)

    @property
    def elements(self) -> set[str]:
        return set(self._elements.keys())

    def merge(self, other: ORSet) -> ORSet:
        """Merge two sets — union of all elements."""
        merged = ORSet()
        all_keys = set(self._elements.keys()) | set(other._elements.keys())
        for key in all_keys:
            ts_self = self._elements.get(key, 0.0)
            ts_other = other._elements.get(key, 0.0)
            merged._elements[key] = max(ts_self, ts_other)
        return merged


@dataclass
class CRDTEngram:
    """An engram with CRDT-based fields for conflict-free multi-agent merge."""

    engram_id: str
    content: LWWRegister = field(default_factory=LWWRegister)
    access_count: GCounter = field(default_factory=GCounter)
    tags: ORSet = field(default_factory=ORSet)
    energy: LWWRegister = field(default_factory=LWWRegister)

    def merge(self, other: CRDTEngram) -> CRDTEngram:
        """Merge two replicas of the same engram."""
        if self.engram_id != other.engram_id:
            msg = f"Cannot merge different engrams: {self.engram_id} vs {other.engram_id}"
            raise ValueError(msg)

        merged = CRDTEngram(
            engram_id=self.engram_id,
            content=self.content.merge(other.content),
            access_count=self.access_count.merge(other.access_count),
            tags=self.tags.merge(other.tags),
            energy=self.energy.merge(other.energy),
        )

        logger.debug(
            "CRDT merge for engram %s: accesses=%d, tags=%s",
            merged.engram_id,
            merged.access_count.value,
            merged.tags.elements,
        )
        return merged
