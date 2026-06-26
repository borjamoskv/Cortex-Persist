import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone


def default_serializer(obj):
    if isinstance(obj, (set, frozenset)):
        return sorted(list(obj))
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def sha256(obj: dict) -> str:
    payload = json.dumps(obj, sort_keys=True, default=default_serializer).encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass
class SwarmEvent:
    task: str
    input: dict
    registry_state: dict
    selected_agent: str
    routing_payload: dict
    version: str = "v2"
    quorum_agents: list[str] | None = None
    entropy_score: float | None = None

    def to_record(self):
        input_hash = sha256(self.input)
        registry_hash = sha256(self.registry_state)

        base = {
            "input_hash": input_hash,
            "registry_hash": registry_hash,
            "selected_agent": self.selected_agent,
            "task": self.task,
            "version": self.version,
            "quorum_agents": self.quorum_agents,
            "entropy_score": self.entropy_score,
        }

        ts = datetime.now(timezone.utc).isoformat()
        event_id = sha256({**base, "timestamp": ts})

        return {
            "event_id": event_id,
            "timestamp": ts,
            **base,
            "routing_payload": json.dumps(
                self.routing_payload, sort_keys=True, default=default_serializer
            ),
            "deterministic_signature": sha256({**base, "routing": self.routing_payload}),
        }
