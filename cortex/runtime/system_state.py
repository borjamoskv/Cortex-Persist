# [C5-REAL] Exergy-Maximized
"""CORTEX Runtime — System State Vector.

The global, numeric, event-sourced state of the entire system.
NOT per-agent state (that's AgentState). This is the organism's
vital signs: entropy, exergy, throughput, error pressure.

Every mutation:
    1. Is caused by an event (causal)
    2. Increments a monotonic tick (temporal)
    3. Produces a new SHA-256 hash (verifiable)
    4. Is stored in an append-only ledger (auditable)

Physics constraints:
    - Entropy ∈ [0.0, 1.0] — system disorder
    - Exergy ∈ [0.0, 1.0] — useful work capacity (1 - entropy)
    - Tick is strictly monotonic
    - No field can violate its domain
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.runtime.system_state")


class SystemPhase(str, Enum):
    """Thermodynamic phase of the system."""
    COLD_START = "cold_start"       # Booting, no agents running
    WARMING = "warming"             # Agents starting, state loading
    NOMINAL = "nominal"             # Normal operation
    HIGH_ENTROPY = "high_entropy"   # Error pressure rising
    CRITICAL = "critical"           # Near failure threshold
    RECOVERY = "recovery"           # Self-healing in progress
    SHUTDOWN = "shutdown"           # Graceful termination


@dataclass
class StateEvent:
    """A single causal event that mutates the SystemStateVector."""
    tick: int
    timestamp: float
    event_type: str
    source: str  # agent_id or "system"
    payload: dict[str, Any] = field(default_factory=dict)
    prev_hash: str = ""
    hash: str = ""

    def compute_hash(self, prev_hash: str) -> str:
        blob = json.dumps(
            {"tick": self.tick, "type": self.event_type,
             "source": self.source, "payload": self.payload,
             "prev": prev_hash},
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode()).hexdigest()


class SystemStateVector:
    """The computable brain of CORTEX.

    Fields (all numeric):
        tick:           int    — monotonic event counter
        entropy:        float  — system disorder [0, 1]
        exergy:         float  — useful work capacity (1 - entropy)
        agents_active:  int    — currently running agents
        agents_total:   int    — total registered agents
        tasks_pending:  int    — unprocessed tasks
        tasks_completed:int    — successfully completed tasks
        tasks_failed:   int    — failed tasks
        error_pressure: float  — rolling error rate [0, 1]
        throughput:     float  — events/second (rolling avg)
        phase:          SystemPhase — current thermodynamic phase

    Invariants:
        - exergy = 1.0 - entropy (always)
        - tick is strictly monotonic
        - 0 <= entropy <= 1
        - 0 <= error_pressure <= 1
    """

    def __init__(self) -> None:
        self.tick: int = 0
        self.entropy: float = 0.0
        self.exergy: float = 1.0
        self.agents_active: int = 0
        self.agents_total: int = 0
        self.tasks_pending: int = 0
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0
        self.error_pressure: float = 0.0
        self.throughput: float = 0.0
        self.phase: SystemPhase = SystemPhase.COLD_START
        self.hash: str = self._genesis_hash()

        # Internal ledger
        self._ledger: list[StateEvent] = []
        self._event_timestamps: list[float] = []
        self._throughput_window: float = 60.0  # seconds

        # Handler dispatch table (bound methods)
        self._handler_map: dict[str, Any] = {
            "agent.started": self._handle_agent_started,
            "agent.stopped": self._handle_agent_stopped,
            "agent.registered": self._handle_agent_registered,
            "task.submitted": self._handle_task_submitted,
            "task.completed": self._handle_task_completed,
            "task.failed": self._handle_task_failed,
            "system.error": self._handle_error,
            "system.recovery": self._handle_recovery,
        }

    # ── Core mutation ────────────────────────────────────────────

    @classmethod
    def bootstrap(cls) -> SystemStateVector:
        """Bootstrap a new SystemStateVector instance."""
        return cls()

    def apply_event(self, event_type: str, source: str,
                    payload: dict[str, Any] | None = None) -> StateEvent:
        """Alias for apply to maintain API compatibility."""
        return self.apply(event_type, source, payload)

    def apply(self, event_type: str, source: str,
              payload: dict[str, Any] | None = None) -> StateEvent:
        """Apply a causal event to the state vector.

        This is the ONLY way to mutate the state.
        Returns the StateEvent for audit.
        """
        payload = payload or {}
        self.tick += 1
        now = time.monotonic()

        event = StateEvent(
            tick=self.tick,
            timestamp=now,
            event_type=event_type,
            source=source,
            payload=payload,
            prev_hash=self.hash,
        )

        # Dispatch to bound handler
        handler = self._handler_map.get(event_type, self._handle_generic)
        handler(payload, source)

        # Recompute derived fields
        self._recompute_thermodynamics(now)

        # Hash chain
        event.hash = event.compute_hash(self.hash)
        self.hash = event.hash

        # Ledger
        self._ledger.append(event)
        self._event_timestamps.append(now)

        logger.debug(
            "[StateVector] tick=%d phase=%s entropy=%.3f exergy=%.3f hash=%s...",
            self.tick, self.phase.value, self.entropy, self.exergy,
            self.hash[:12],
        )
        return event

    # ── Event handlers ───────────────────────────────────────────

    def _handle_agent_started(self, payload: dict, source: str) -> None:
        self.agents_active += 1
        self.agents_total = max(self.agents_total, self.agents_active)

    def _handle_agent_stopped(self, payload: dict, source: str) -> None:
        self.agents_active = max(0, self.agents_active - 1)

    def _handle_agent_registered(self, payload: dict, source: str) -> None:
        self.agents_total += 1

    def _handle_task_submitted(self, payload: dict, source: str) -> None:
        self.tasks_pending += 1

    def _handle_task_completed(self, payload: dict, source: str) -> None:
        self.tasks_pending = max(0, self.tasks_pending - 1)
        self.tasks_completed += 1

    def _handle_task_failed(self, payload: dict, source: str) -> None:
        self.tasks_pending = max(0, self.tasks_pending - 1)
        self.tasks_failed += 1

    def _handle_error(self, payload: dict, source: str) -> None:
        # Error pressure increases with each error
        self.error_pressure = min(1.0, self.error_pressure + 0.1)

    def _handle_recovery(self, payload: dict, source: str) -> None:
        # Recovery reduces error pressure
        self.error_pressure = max(0.0, self.error_pressure - 0.2)

    def _handle_generic(self, payload: dict, source: str) -> None:
        pass  # Unknown event types are recorded but don't mutate numeric state



    # ── Thermodynamic derivation ─────────────────────────────────

    def _recompute_thermodynamics(self, now: float) -> None:
        """Derive entropy, exergy, throughput, phase from raw counters."""
        # Throughput: events in the last window
        cutoff = now - self._throughput_window
        self._event_timestamps = [
            t for t in self._event_timestamps if t > cutoff
        ]
        self.throughput = len(self._event_timestamps) / self._throughput_window

        # Entropy: weighted combination of error pressure + task failure ratio
        total_tasks = self.tasks_completed + self.tasks_failed
        failure_ratio = (self.tasks_failed / total_tasks) if total_tasks > 0 else 0.0
        self.entropy = min(1.0, 0.6 * self.error_pressure + 0.4 * failure_ratio)
        self.exergy = 1.0 - self.entropy

        # Phase transitions
        self.phase = self._derive_phase()

    def _derive_phase(self) -> SystemPhase:
        """Deterministic phase derivation from numeric state."""
        if self.agents_active == 0 and self.tick <= 1:
            return SystemPhase.COLD_START
        if self.agents_active == 0 and self.tick > 1:
            return SystemPhase.SHUTDOWN
        if self.error_pressure >= 0.8:
            return SystemPhase.CRITICAL
        if self.entropy >= 0.5:
            return SystemPhase.HIGH_ENTROPY
        if self.error_pressure > 0 and self.error_pressure < 0.3:
            return SystemPhase.RECOVERY
        if self.agents_active > 0 and self.entropy < 0.2:
            return SystemPhase.NOMINAL
        return SystemPhase.WARMING

    # ── Query ────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """Return a complete numeric snapshot of the state vector."""
        return {
            "tick": self.tick,
            "entropy": round(self.entropy, 4),
            "exergy": round(self.exergy, 4),
            "agents_active": self.agents_active,
            "agents_total": self.agents_total,
            "tasks_pending": self.tasks_pending,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "error_pressure": round(self.error_pressure, 4),
            "throughput": round(self.throughput, 4),
            "phase": self.phase.value,
            "hash": self.hash,
        }

    def ledger_tail(self, n: int = 10) -> list[dict[str, Any]]:
        """Return the last N events from the ledger."""
        return [
            {
                "tick": e.tick,
                "type": e.event_type,
                "source": e.source,
                "hash": e.hash[:16],
            }
            for e in self._ledger[-n:]
        ]

    @property
    def is_healthy(self) -> bool:
        return self.phase in (SystemPhase.NOMINAL, SystemPhase.WARMING)

    def hash_chain_valid(self) -> bool:
        """Verify the integrity of the entire ledger hash chain.

        Walks every event in the ledger and confirms:
            1. Each event's hash matches its recomputed hash from prev_hash.
            2. The chain links are contiguous (event.prev_hash == previous event.hash).
            3. The final hash in the chain matches self.hash.

        Returns True if the chain is intact, False on any break.
        """
        if not self._ledger:
            return True  # Empty ledger, genesis only

        expected_prev = self._genesis_hash()
        for event in self._ledger:
            if event.prev_hash != expected_prev:
                logger.error(
                    "Hash chain break at tick %d: expected prev=%s, got=%s",
                    event.tick, expected_prev[:16], event.prev_hash[:16],
                )
                return False
            recomputed = event.compute_hash(event.prev_hash)
            if event.hash != recomputed:
                logger.error(
                    "Hash mismatch at tick %d: stored=%s, recomputed=%s",
                    event.tick, event.hash[:16], recomputed[:16],
                )
                return False
            expected_prev = event.hash

        if self.hash != expected_prev:
            logger.error(
                "Final hash mismatch: state=%s, chain_tail=%s",
                self.hash[:16], expected_prev[:16],
            )
            return False
        return True

    def _genesis_hash(self) -> str:
        return hashlib.sha256(b"CORTEX_GENESIS_STATE_v1").hexdigest()
