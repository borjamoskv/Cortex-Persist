from dataclasses import dataclass, field
import uuid
from typing import Any

@dataclass
class EventV1:
    """Event V1 schema."""
    event_type: str
    source: str
    skill_id: str
    payload: dict[str, Any]
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
