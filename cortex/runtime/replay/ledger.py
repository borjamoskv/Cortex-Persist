# [C5-REAL] Exergy-Maximized
from typing import Any


class EventLedger:
    """Fuente única de verdad replayable. Almacena mutaciones en orden causal."""

    def __init__(self):
        self.events = []

    def append(self, event: dict[str, Any]):
        self.events.append(event)

    def export(self) -> list[dict[str, Any]]:
        return self.events
