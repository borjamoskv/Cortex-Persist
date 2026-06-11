"""Trace adapter: canonical types for E1 profiler and MetaArbiterKernel.

Provides ExecutionTrace and TraceEvent — the stable boundary between
the live runtime (CortexEngine) and the observability layer (E1, phase detector).

Does NOT import from cortex.engine to avoid circular dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class TraceEvent:
    """Single observable event within an execution trajectory."""

    kind: str  # "write" | "read" | "mutation" | "fact" | "commit"
    fact_id: str | None
    tenant_id: str | None
    timestamp: float
    ledger_height: int | None
    payload_hash: str | None
    is_write: bool = False
    is_read: bool = False
    is_mutation: bool = False
    is_persisted_event: bool = False


@dataclass
class ExecutionTrace:
    """Observable execution trajectory.

    Wraps audit_log + ledger events from CortexEngine into a form that
    satisfies the Trajectory Protocol expected by MetaArbiterKernel and
    energy_fn components.

    Attributes
    ----------
    id:            Unique trace identifier (UUID).
    tenant_id:     Tenant scope, or None for system-level traces.
    model_version: Version tag of the model/engine that produced the trace.
    op_kind:       High-level operation type: "write", "query", "mutation", "agent".
    start_time:    Monotonic start time (seconds).
    end_time:      Monotonic end time (seconds).
    """

    id: str
    tenant_id: str | None
    model_version: str
    op_kind: str
    start_time: float
    end_time: float
    _events: list[TraceEvent] = field(default_factory=list)

    # --- Trajectory Protocol interface ---

    def events(self) -> Iterator[TraceEvent]:
        """Iterate over all recorded events in order."""
        yield from self._events

    def length(self) -> int:
        """Number of recorded events."""
        return len(self._events)

    def ledger_snapshot(self) -> int | None:
        """Ledger height at the end of the trace (last known value)."""
        for ev in reversed(self._events):
            if ev.ledger_height is not None:
                return ev.ledger_height
        return None

    def wall_time(self) -> float:
        """Total wall-clock duration in seconds."""
        return max(0.0, self.end_time - self.start_time)

    # --- Convenience counters (used by TrajectoryEmbedding morphology layer) ---

    def writes_count(self) -> int:
        return sum(1 for ev in self._events if ev.is_write)

    def reads_count(self) -> int:
        return sum(1 for ev in self._events if ev.is_read)

    def mutations_count(self) -> int:
        return sum(1 for ev in self._events if ev.is_mutation)

    def persisted_events(self) -> list[TraceEvent]:
        """Events that touch the ledger (writes, commits, facts)."""
        return [ev for ev in self._events if ev.is_persisted_event]

    def as_dict(self) -> dict[str, Any]:
        """Lightweight serialization for jsonl logging."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "model_version": self.model_version,
            "op_kind": self.op_kind,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "length": self.length(),
            "ledger_snapshot": self.ledger_snapshot(),
            "wall_time": self.wall_time(),
            "writes": self.writes_count(),
            "reads": self.reads_count(),
            "mutations": self.mutations_count(),
        }
