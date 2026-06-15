import json
import hashlib
from dataclasses import dataclass
from datetime import datetime


def sha256(obj: dict) -> str:
    payload = json.dumps(obj, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass
class SwarmEvent:
    task: str
    input: dict
    registry_state: dict
    selected_agent: str
    routing_payload: dict
    version: str = "v2"

    def to_record(self):
        input_hash = sha256(self.input)
        registry_hash = sha256(self.registry_state)

        base = {
            "input_hash": input_hash,
            "registry_hash": registry_hash,
            "selected_agent": self.selected_agent,
            "task": self.task,
            "version": self.version,
        }

        event_id = sha256(base)

        return {
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
            **base,
            "routing_payload": json.dumps(self.routing_payload, sort_keys=True),
            "deterministic_signature": sha256({**base, "routing": self.routing_payload}),
        }
