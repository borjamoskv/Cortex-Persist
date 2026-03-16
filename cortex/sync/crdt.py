"""
CRDT Merge Engine — Conflict-Free Replication for Agent Swarms (Ω₃ / Ω₁₂).

Implements Local-First persistence for multi-agent swarms:
  - Agents mutate memory locally without connection or locks.
  - On reconnection, CRDTs merge deterministically.

Data Structures:
  - LWW-Register (Last-Writer-Wins): For mutable facts (events, observations).
    The fact with the highest HLC timestamp wins.
  - MV-Register (Multi-Value): For critical facts (decisions, axioms).
    Both versions are preserved with a conflict flag for manual resolution.

Edge-compatible: Pure Python, SQLite-only, no external services.
GPU-native: N/A (merge is CPU-bound, O(N log N) via sorted merge).
AGI-ready: Supports unbounded number of agents/nodes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cortex.sync.hlc import HLCTimestamp

logger = logging.getLogger("cortex.sync.crdt")

__all__ = [
    "CortexCRDT",
    "MergeResult",
    "FactReplica",
    "ConflictRecord",
]

# Fact types that use MV-Register (preserve both sides on conflict)
_CRITICAL_TYPES = frozenset({"decision", "axiom", "rule", "belief"})


@dataclass
class FactReplica:
    """A fact as seen by a specific node.

    Contains the HLC timestamp for causal ordering
    and the node_id to identify the source agent.
    """

    fact_id: int
    content: str
    fact_type: str
    project: str
    hlc: HLCTimestamp
    node_id: int
    confidence: str = "C3"
    meta: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    source: str | None = None
    is_tombstoned: bool = False

    @property
    def is_critical(self) -> bool:
        """Critical facts use MV-Register (both sides preserved)."""
        return self.fact_type in _CRITICAL_TYPES


@dataclass
class ConflictRecord:
    """A detected conflict between two replicas of a critical fact."""

    fact_id: int
    fact_type: str
    project: str
    local_content: str
    remote_content: str
    local_hlc: HLCTimestamp
    remote_hlc: HLCTimestamp
    local_node: int
    remote_node: int
    resolution: str = "pending"  # "pending" | "local_wins" | "remote_wins"

    def resolve_local(self) -> None:
        self.resolution = "local_wins"

    def resolve_remote(self) -> None:
        self.resolution = "remote_wins"


@dataclass
class MergeResult:
    """Outcome of a CRDT merge operation between two nodes."""

    facts_added: int = 0
    facts_updated: int = 0
    facts_identical: int = 0
    conflicts_detected: int = 0
    conflicts: list[ConflictRecord] = field(default_factory=list)
    tombstones_applied: int = 0
    total_processed: int = 0

    @property
    def had_conflicts(self) -> bool:
        return self.conflicts_detected > 0


class CortexCRDT:
    """Conflict-Free Replicated Data Type engine for CORTEX facts.

    Merges two sets of fact replicas using:
      - LWW-Register for non-critical facts (latest HLC wins)
      - MV-Register for critical facts (both preserved, conflict flagged)
    """

    def __init__(self, local_node_id: int = 0):
        self._local_node_id = local_node_id

    def merge(
        self,
        local_facts: list[FactReplica],
        remote_facts: list[FactReplica],
    ) -> MergeResult:
        """Merge remote facts into local state.

        Returns a MergeResult describing all changes.
        The caller is responsible for applying the result to the DB.

        Algorithm:
          1. Index local facts by (project, fact_id)
          2. For each remote fact:
             a. If not in local → ADD
             b. If in local with same content → SKIP
             c. If in local with different content:
                - Non-critical: LWW (highest HLC wins) → UPDATE
                - Critical: MV-Register → CONFLICT (both preserved)
        """
        result = MergeResult()

        # Index local facts for O(1) lookup
        local_index: dict[tuple[str, int], FactReplica] = {}
        for fact in local_facts:
            local_index[(fact.project, fact.fact_id)] = fact

        for remote in remote_facts:
            result.total_processed += 1
            key = (remote.project, remote.fact_id)

            # Handle tombstones (deletions)
            if remote.is_tombstoned:
                if key in local_index and not local_index[key].is_tombstoned:
                    result.tombstones_applied += 1
                continue

            local = local_index.get(key)

            if local is None:
                # New fact — ADD
                result.facts_added += 1
                continue

            if local.content == remote.content:
                # Identical — SKIP
                result.facts_identical += 1
                continue

            # Content differs — resolve by type
            if remote.is_critical:
                # MV-Register: preserve both, flag conflict
                conflict = ConflictRecord(
                    fact_id=remote.fact_id,
                    fact_type=remote.fact_type,
                    project=remote.project,
                    local_content=local.content,
                    remote_content=remote.content,
                    local_hlc=local.hlc,
                    remote_hlc=remote.hlc,
                    local_node=local.node_id,
                    remote_node=remote.node_id,
                )
                result.conflicts.append(conflict)
                result.conflicts_detected += 1
                logger.warning(
                    "MV-Register conflict: fact #%d (%s) local@node%d vs remote@node%d",
                    remote.fact_id,
                    remote.fact_type,
                    local.node_id,
                    remote.node_id,
                )
            else:
                # LWW-Register: highest HLC wins
                if remote.hlc > local.hlc:
                    result.facts_updated += 1
                elif remote.hlc == local.hlc:
                    # Tie-break by node_id (deterministic)
                    if remote.node_id > local.node_id:
                        result.facts_updated += 1
                    else:
                        result.facts_identical += 1
                else:
                    result.facts_identical += 1

        return result

    def resolve_conflicts(
        self,
        conflicts: list[ConflictRecord],
        strategy: str = "latest",
    ) -> list[ConflictRecord]:
        """Auto-resolve conflicts using a strategy.

        Strategies:
          - "latest": Higher HLC wins (converts MV → LWW behavior)
          - "local": Local always wins
          - "remote": Remote always wins
          - "manual": Leave as pending (default for critical facts)
        """
        for conflict in conflicts:
            if strategy == "latest":
                if conflict.remote_hlc > conflict.local_hlc:
                    conflict.resolve_remote()
                else:
                    conflict.resolve_local()
            elif strategy == "local":
                conflict.resolve_local()
            elif strategy == "remote":
                conflict.resolve_remote()
            # "manual" → leave as pending

        return conflicts
