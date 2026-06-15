from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class MorphSnapshot:
    snapshot_id: str
    agents_hash: str
    contracts_hash: str
    timestamp: float
    prev_hash: str | None


class MorphRegistry:
    def __init__(self) -> None:
        self.chain: list[dict[str, Any]] = []
        self.handlers: dict[str, Any] = {}

    def register_handler(self, name: str, handler: Any) -> None:
        if name in self.handlers:
            raise ValueError(f"Handler '{name}' already registered")
        self.handlers[name] = handler

    def get_handler(self, name: str) -> Any:
        return self.handlers.get(name)

    def load_agents_md(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def compute_agents_hash(self, agents_md: str) -> str:
        return _sha256_text(agents_md)

    def compute_contracts_hash(self, contracts: dict[str, Any]) -> str:
        return _sha256_text(_canonical_json(contracts))

    def record_snapshot(
        self,
        agents_md: str,
        contracts: dict[str, Any],
    ) -> MorphSnapshot:
        agents_hash = self.compute_agents_hash(agents_md)
        contracts_hash = self.compute_contracts_hash(contracts)
        prev_hash = self.chain[-1]["snapshot_id"] if self.chain else None

        snapshot_payload = {
            "agents_hash": agents_hash,
            "contracts_hash": contracts_hash,
            "prev_hash": prev_hash,
            "timestamp": time.time(),
        }
        snapshot_id = _sha256_text(_canonical_json(snapshot_payload))

        snapshot = MorphSnapshot(
            snapshot_id=snapshot_id,
            agents_hash=agents_hash,
            contracts_hash=contracts_hash,
            timestamp=snapshot_payload["timestamp"],
            prev_hash=prev_hash,
        )
        self.chain.append(asdict(snapshot))
        return snapshot

    def current_snapshot(self) -> MorphSnapshot | None:
        if not self.chain:
            return None
        return MorphSnapshot(**self.chain[-1])

    def current_target_hash(self) -> str | None:
        snap = self.current_snapshot()
        return snap.snapshot_id if snap else None
