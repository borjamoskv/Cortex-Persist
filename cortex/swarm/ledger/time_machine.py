from __future__ import annotations

import copy
import json
from dataclasses import dataclass

from .engine import SwarmLedger


@dataclass
class ForkResult:
    """
    Result of a fork() operation.
    Carries the registry snapshot at the divergence point
    and full metadata for auditability.
    """

    origin_event_id: str
    origin_timestamp: str
    origin_task: str
    origin_selected_agent: str
    registry_snapshot: dict  # deep copy of registry state at fork point
    events_before_fork: list[dict]  # full history up to and including fork point


class SwarmTimeMachine:
    """
    High-level time-travel API over SwarmLedger.

    Operations:
      - replay_from(ts)          → slice of events from timestamp
      - fork(event_id)           → ForkResult with isolated registry snapshot
      - diff(event_id_a, b)      → divergence delta between two fork points
    """

    def __init__(self, ledger: SwarmLedger):
        self.ledger = ledger

    # ------------------------------------------------------------------
    # Time-travel replay
    # ------------------------------------------------------------------

    def replay_from(self, ts: str, task: str | None = None) -> list[dict]:
        """
        Replay all events at or after `ts`.
        Returns ordered list of event dicts.
        """
        return self.ledger.replay_from_timestamp(ts, task=task)

    # ------------------------------------------------------------------
    # Fork
    # ------------------------------------------------------------------

    def fork(self, event_id: str) -> ForkResult:
        """
        Clone the registry state at `event_id`.
        Returns a ForkResult with an isolated deep copy —
        mutating it does not affect the ledger or any other fork.
        """
        event = self.ledger.get_event(event_id)
        if event is None:
            raise ValueError(f"event_id not found: {event_id}")

        # Reconstruct registry snapshot from the stored registry_hash context.
        # The routing_payload is stored as JSON string; parse it back.
        routing_payload = json.loads(event["routing_payload"])

        # Build a minimal registry snapshot from what was recorded.
        # Full reconstruction requires the original registry.snapshot() —
        # here we store the deterministic hash-verified subset.
        registry_snapshot = {
            "agent_id": event["selected_agent"],
            "task": event["task"],
            "registry_hash": event["registry_hash"],
            "routing_payload": routing_payload,
            "version": event["version"],
        }

        # Collect all events up to and including this fork point
        all_events = self.ledger.all_events()
        pivot_id = event["id"] if "id" in event else None
        events_before = [e for e in all_events if pivot_id is None or e.get("id", 0) <= pivot_id]

        return ForkResult(
            origin_event_id=event_id,
            origin_timestamp=event["timestamp"],
            origin_task=event["task"],
            origin_selected_agent=event["selected_agent"],
            registry_snapshot=copy.deepcopy(registry_snapshot),
            events_before_fork=copy.deepcopy(events_before),
        )

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

    def diff(self, event_id_a: str, event_id_b: str) -> dict:
        """
        Returns the divergence delta between two fork points.
        Useful for detecting where two execution paths split.
        """
        fork_a = self.fork(event_id_a)
        fork_b = self.fork(event_id_b)

        return {
            "diverges_at_agent": fork_a.origin_selected_agent != fork_b.origin_selected_agent,
            "agent_a": fork_a.origin_selected_agent,
            "agent_b": fork_b.origin_selected_agent,
            "registry_hash_a": fork_a.registry_snapshot["registry_hash"],
            "registry_hash_b": fork_b.registry_snapshot["registry_hash"],
            "hashes_match": fork_a.registry_snapshot["registry_hash"]
            == fork_b.registry_snapshot["registry_hash"],
            "events_before_a": len(fork_a.events_before_fork),
            "events_before_b": len(fork_b.events_before_fork),
        }
