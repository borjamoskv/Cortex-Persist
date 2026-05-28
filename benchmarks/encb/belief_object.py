"""ENCB v2 — Typed Belief Objects.

Four claim types with CRDT-compatible version vectors, evidence chains,
and conflict sets. Mutable dataclass — merge operations mutate in place
for simulation performance.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BeliefType(str, Enum):
    """The four proposition types supported by the benchmark."""

    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"
    SCALAR = "scalar"
    SET = "set"


@dataclass(frozen=True)
class Evidence:
    """A single observation supporting or contesting a belief.

    Immutable — evidence records are append-only.
    """

    source_node: str
    timestamp: int
    confidence: float  # 0..1
    assumption_ids: frozenset[str]
    payload_hash: str
    value: Any = None

    @staticmethod
    def make(
        node: str,
        t: int,
        conf: float,
        key: str,
        value: Any,
        assumptions: frozenset[str] | None = None,
    ) -> Evidence:
        """Factory for common evidence creation."""
        return Evidence(
            source_node=node,
            timestamp=t,
            confidence=max(0.0, min(1.0, conf)),
            assumption_ids=assumptions or frozenset(),
            payload_hash=f"{key}:{value}:{t}:{node}",
            value=value,
        )


@dataclass
class BeliefObject:
    """Typed belief with CRDT version vector and evidence chain.

    This is the atomic unit of the ENCB benchmark. Each belief represents
    a single proposition in the simulated universe.

    Attributes:
        belief_id: Unique identifier.
        proposition_key: The proposition this belief is about.
        belief_type: One of BOOLEAN, CATEGORICAL, SCALAR, SET.
        value: Current resolved value (type depends on belief_type).
        confidence: Aggregate confidence [0, 1].
        version_vector: Node → logical clock mapping (Lamport / vector clock).
        evidences: Ordered list of supporting evidence records.
        conflict_set: IDs of beliefs in active conflict with this one.
        tombstoned: Whether this belief has been logically deleted.
        semantic_domain: Domain label for grouping (e.g., "config", "model").
    """

    belief_id: str
    proposition_key: str
    belief_type: BeliefType
    value: Any
    confidence: float
    version_vector: dict[str, int]
    evidences: list[Evidence] = field(default_factory=list)
    conflict_set: set[str] = field(default_factory=set)
    tombstoned: bool = False
    semantic_domain: str = "general"

    @staticmethod
    def new(
        key: str,
        belief_type: BeliefType,
        value: Any,
        node: str,
        t: int,
        conf: float,
        domain: str = "general",
    ) -> BeliefObject:
        """Create a fresh belief from a single initial observation."""
        return BeliefObject(
            belief_id=str(uuid.uuid4()),
            proposition_key=key,
            belief_type=belief_type,
            value=value,
            confidence=max(0.0, min(1.0, conf)),
            version_vector={node: 1},
            evidences=[
                Evidence.make(node, t, conf, key, value),
            ],
            semantic_domain=domain,
        )

    def add_evidence(self, ev: Evidence, node: str) -> None:
        """Append evidence and bump the version vector for the source node."""
        self.evidences.append(ev)
        self.version_vector[node] = self.version_vector.get(node, 0) + 1

    @property
    def latest_timestamp(self) -> int:
        """Most recent evidence timestamp."""
        if not self.evidences:
            return 0
        return max(e.timestamp for e in self.evidences)

    def dominates(self, other: BeliefObject) -> bool:
        """Check if this belief's version vector dominates another's.

        Returns True if every entry in other's VV is <= this one's,
        and at least one is strictly greater.
        """
        all_nodes = set(self.version_vector) | set(other.version_vector)
        geq = True
        strictly_greater = False
        for node in all_nodes:
            mine = self.version_vector.get(node, 0)
            theirs = other.version_vector.get(node, 0)
            if mine < theirs:
                geq = False
                break
            if mine > theirs:
                strictly_greater = True
        return geq and strictly_greater

    def concurrent_with(self, other: BeliefObject) -> bool:
        """True if neither version vector dominates the other."""
        return not self.dominates(other) and not other.dominates(self)
