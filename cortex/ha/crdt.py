"""
CORTEX v5.0 — Conflict-Free Replicated Data Types (CRDTs).

Provides data structures for eventual consistency in HA clusters.
"""

from dataclasses import dataclass, field
from typing import Generic, TypeVar

__all__ = [
    "LWWRegister",
    "ORSet",
    "T",
    "VectorClock",
]

T = TypeVar("T")


@dataclass
class VectorClock:
    """
    Vector clock for causality tracking.
    """

    node_id: str
    counters: dict[str, int] = field(default_factory=dict)

    def increment(self) -> "VectorClock":
        """Increment this node's counter."""
        new_counters = self.counters.copy()
        new_counters[self.node_id] = new_counters.get(self.node_id, 0) + 1
        return VectorClock(self.node_id, new_counters)

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Merge with another vector clock (taking max of each counter)."""
        all_nodes = set(self.counters.keys()) | set(other.counters.keys())
        new_counters = {}
        for node in all_nodes:
            new_counters[node] = max(self.counters.get(node, 0), other.counters.get(node, 0))
        return VectorClock(self.node_id, new_counters)

    def compare(self, other: "VectorClock") -> str:
        """
        Compare two vector clocks.

        Returns:
            - 'before': self happened before other
            - 'after': self happened after other
            - 'equal': self and other are identical
            - 'concurrent': neither happened before the other
        """
        all_nodes = set(self.counters.keys()) | set(other.counters.keys())
        dominates = False
        dominated = False

        for node in all_nodes:
            a = self.counters.get(node, 0)
            b = other.counters.get(node, 0)
            if a > b:
                dominates = True
            elif b > a:
                dominated = True

        if dominates and not dominated:
            return "after"
        if dominated and not dominates:
            return "before"
        if not dominates and not dominated:
            return "equal"
        return "concurrent"


@dataclass
class LWWRegister(Generic[T]):
    """
    Last-Write-Wins Register.
    Does not require vector clocks, relies on wall clock timestamp.
    """

    value: T
    timestamp: float

    def merge(self, other: "LWWRegister[T]") -> "LWWRegister[T]":
        if other.timestamp > self.timestamp:
            return other
        elif other.timestamp < self.timestamp:
            return self
        else:
            # Tie-breaker: arbitrary but deterministic (e.g. value hash or comparison)
            # Here we just keep self if equal
            return self


class ORSet(Generic[T]):
    """
    Observed-Remove Set (Add-Wins Set).
    Allows adding and removing elements concurrently.
    """

    def __init__(self):
        # State: set of (element, uuid) pairs.
        # Add(e, uid) → state ∪ {(e, uid)}
        # Remove(e) → drop all (e, *) pairs known locally.
        self._state: set[tuple[T, str]] = set()

    def add(self, element: T, uid: str):
        self._state.add((element, uid))

    def remove(self, element: T):
        # Remove all instances of this element currently known
        to_remove = {item for item in self._state if item[0] == element}
        self._state -= to_remove

    def merge(self, other: "ORSet[T]") -> "ORSet[T]":
        """Merge two OR-Sets using state-based Add-Wins semantics.

        Union of (element, uuid) pairs.  A concurrent Add always wins
        over a concurrent Remove because the Add introduces a fresh uuid
        that the Remove has never observed.

        Returns self (mutated in-place) for a fluent interface.
        """
        self._state |= other._state
        return self
