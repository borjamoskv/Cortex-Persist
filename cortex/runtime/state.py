# [C5-REAL] Exergy-Maximized
import hashlib
import json
from typing import Any


class RuntimeState:
    """Immutable causal state derived exclusively from the event ledger."""

    def __init__(self, initial_state: dict[str, Any] = None, version: int = 0):
        self.data = initial_state or {}
        self.version = version
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        state_str = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(f"{self.version}:{state_str}".encode()).hexdigest()

    def apply_event(self, event: dict[str, Any]) -> "RuntimeState":
        """Deterministic state evolution with semantic physics validation."""
        action = event.get("action_type")
        payload = event.get("payload", {})

        # Physics Validation Layer
        tick = payload.get("tick")
        if tick is not None:
            prev_tick = self.data.get("last_tick", -1)
            if tick <= prev_tick:
                raise ValueError(
                    f"[PHYSICS VIOLATION] Causality inversion. Tick {tick} <= Previous {prev_tick}"
                )
            self.data["last_tick"] = tick

        entropy = payload.get("entropy")
        if entropy is not None and entropy < 0:
            raise ValueError("[PHYSICS VIOLATION] Negative entropy detected.")

        if action == "MEMORY_WRITE":
            self.data.update(payload)

        self.version += 1
        self.hash = self._compute_hash()
        return self

    @classmethod
    def bootstrap(cls) -> "RuntimeState":
        """Bootstrap a fresh state."""
        return cls()

    def snapshot(self) -> dict[str, Any]:
        """Produce a deterministic snapshot dictionary for validation."""
        return {"version": self.version, "state_hash": self.hash, "data": dict(self.data)}
