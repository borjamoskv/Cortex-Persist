# [C5-REAL] Exergy-Maximized
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EventV1:
    """Event V1 strict schema."""
    event_type: str
    source: str
    skill_id: str
    payload: dict[str, Any]
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Validate critical boundaries for Event V1."""
        if not self.event_type or not isinstance(self.event_type, str):
            raise ValueError("EventV1 requires a valid 'event_type' string")
        if not self.skill_id or not isinstance(self.skill_id, str):
            raise ValueError("EventV1 requires a valid 'skill_id' string")
        if not isinstance(self.payload, dict):
            raise ValueError("EventV1 'payload' must be a dictionary")
