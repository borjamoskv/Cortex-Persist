# Cortex-Persist :: Event-Sourced Brain Simulator (C4-SIM)
# Deterministic replayable connectome execution model

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import time
import json

@dataclass
class BrainEvent:
    ts: float
    source: str
    target: str
    event_type: str
    payload: Dict[str, Any]

class EventStore:
    def __init__(self):
        self.events: List[BrainEvent] = []

    def append(self, event: BrainEvent):
        self.events.append(event)

    def replay(self):
        state = {}
        for e in self.events:
            state.setdefault(e.target, []).append(e)
        return state

class BrainGraph:
    def __init__(self):
        self.store = EventStore()

    def emit(self, source, target, event_type, payload=None):
        event = BrainEvent(
            ts=time.time(),
            source=source,
            target=target,
            event_type=event_type,
            payload=payload or {}
        )
        self.store.append(event)

    def route_signal(self, signal: str):
        routing_table = {
            "talamo": ["occipital", "parietal", "temporal"],
            "amigdala": ["prefrontal"],
            "hipocampo": ["prefrontal"],
            "ganglios_basales": ["frontal"],
        }

        for source, targets in routing_table.items():
            for t in targets:
                self.emit(source, t, "signal_route", {"signal": signal})

    def dump(self):
        return json.dumps([asdict(e) for e in self.store.events], indent=2)

if __name__ == "__main__":
    brain = BrainGraph()

    # deterministic stimulus injection
    brain.route_signal("C4_SIM_BOOT")
    brain.route_signal("SENSORY_STREAM")

    print(brain.dump())
