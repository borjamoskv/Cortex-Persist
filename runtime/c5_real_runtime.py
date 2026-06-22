from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Optional

# -----------------------------
# Event Model
# -----------------------------


@dataclass(frozen=True)
class Event:
    id: str
    timestamp: int
    type: str
    payload: dict[str, Any]
    actor: str
    parent_hash: Optional[str] = None

    def canonical(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def hash(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()


# -----------------------------
# Event Store (append-only)
# -----------------------------


class EventStore:
    def __init__(self):
        self._events: list[Event] = []

    def append(self, event: Event) -> str:
        if self._events:
            last = self._events[-1].hash()
            if event.parent_hash and event.parent_hash != last:
                raise ValueError("Invalid parent hash (fork detected)")
        object.__setattr__(event, "parent_hash", self._events[-1].hash() if self._events else None)
        self._events.append(event)
        return event.hash()

    def all(self) -> list[Event]:
        return list(self._events)


# -----------------------------
# Merkle Root
# -----------------------------


class Merkle:
    @staticmethod
    def root(events: list[Event]) -> str:
        if not events:
            return ""

        layer = [e.hash().encode() for e in events]

        while len(layer) > 1:
            if len(layer) % 2 == 1:
                layer.append(layer[-1])

            next_layer = []
            for i in range(0, len(layer), 2):
                combined = hashlib.sha256(layer[i] + layer[i + 1]).hexdigest().encode()
                next_layer.append(combined)

            layer = next_layer

        return layer[0].decode()


# -----------------------------
# Replay Engine
# -----------------------------


class ReplayEngine:
    def __init__(self, store: EventStore):
        self.store = store

    def replay(self) -> dict[str, Any]:
        state: dict[str, Any] = {}

        for event in self.store.all():
            state = self._apply(state, event)

        return state

    def _apply(self, state: dict[str, Any], event: Event) -> dict[str, Any]:
        # deterministic reducer
        if event.type == "SET":
            key = event.payload["key"]
            value = event.payload["value"]
            state[key] = value

        elif event.type == "INC":
            key = event.payload["key"]
            state[key] = state.get(key, 0) + event.payload.get("value", 1)

        elif event.type == "DELETE":
            key = event.payload["key"]
            state.pop(key, None)

        return state


# -----------------------------
# Authority Graph (minimal)
# -----------------------------


class AuthorityGraph:
    def __init__(self):
        self.edges: dict[str, list[str]] = {}

    def auth(self, parent: str, child: str):
        self.edges.setdefault(parent, []).append(child)

    def revoke(self, parent: str, child: str):
        if parent in self.edges:
            self.edges[parent] = [c for c in self.edges[parent] if c != child]

    def is_authorized(self, parent: str, child: str) -> bool:
        return child in self.edges.get(parent, [])


# -----------------------------
# C5-REAL Kernel
# -----------------------------


class C5RealKernel:
    def __init__(self):
        self.store = EventStore()
        self.replay_engine = ReplayEngine(self.store)
        self.auth = AuthorityGraph()

    def commit(self, event: Event) -> str:
        return self.store.append(event)

    def state(self) -> dict[str, Any]:
        return self.replay_engine.replay()

    def merkle_root(self) -> str:
        return Merkle.root(self.store.all())
