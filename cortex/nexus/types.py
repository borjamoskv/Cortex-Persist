"""
CORTEX Nexus Domain Types (Zero-Trust).
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class DomainOrigin(Enum):
    """Typed origin for every mutation."""

    MAILTV = auto()
    MOLTBOOK = auto()
    CORTEX_CORE = auto()
    SAP_AUDIT = auto()
    DAEMON = auto()


class IntentType(Enum):
    """O(1) intent classification."""

    # MailTV
    EMAIL_INTERCEPTED = auto()
    EMAIL_REPLIED = auto()
    EMAIL_ARCHIVED = auto()
    SENDER_CLASSIFIED = auto()
    # Moltbook
    POST_PUBLISHED = auto()
    KARMA_LAUNDERED = auto()
    SHADOWBAN_DETECTED = auto()
    ENGAGEMENT_SPIKE = auto()
    # CORTEX Core
    DECISION_STORED = auto()
    GHOST_DETECTED = auto()
    GHOST_WATCH_TRIGGER = auto()
    BRIDGE_FORMED = auto()
    HEARTBEAT_PULSE = auto()
    SLEEP_CYCLE_TRIGGERED = auto()
    # SAP Audit
    ANOMALY_DETECTED = auto()
    AUDIT_COMPLETED = auto()


class Priority(Enum):
    """Mutation priority. Lower value = higher urgency."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


_INTENT_PRIORITY: dict[IntentType, Priority] = {
    IntentType.SHADOWBAN_DETECTED: Priority.CRITICAL,
    IntentType.ANOMALY_DETECTED: Priority.CRITICAL,
    IntentType.EMAIL_INTERCEPTED: Priority.HIGH,
    IntentType.POST_PUBLISHED: Priority.HIGH,
    IntentType.GHOST_DETECTED: Priority.HIGH,
    IntentType.GHOST_WATCH_TRIGGER: Priority.HIGH,
    IntentType.KARMA_LAUNDERED: Priority.NORMAL,
    IntentType.ENGAGEMENT_SPIKE: Priority.NORMAL,
    IntentType.EMAIL_REPLIED: Priority.NORMAL,
    IntentType.SENDER_CLASSIFIED: Priority.NORMAL,
    IntentType.DECISION_STORED: Priority.NORMAL,
    IntentType.BRIDGE_FORMED: Priority.NORMAL,
    IntentType.HEARTBEAT_PULSE: Priority.LOW,
    IntentType.SLEEP_CYCLE_TRIGGERED: Priority.LOW,
    IntentType.AUDIT_COMPLETED: Priority.LOW,
    IntentType.EMAIL_ARCHIVED: Priority.LOW,
}


@dataclass(frozen=True)
class WorldMutation:
    """Immutable, typed, hashed record of a change to the World Model."""

    origin: DomainOrigin
    intent: IntentType
    project: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    priority: Priority = Priority.NORMAL

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence {self.confidence} out of [0.0, 1.0]")
        if not self.project:
            raise ValueError("Project must be non-empty")

    @property
    def idempotency_key(self) -> str:
        """SHA-256 hash of the mutation's semantic content for dedup."""
        payload_repr = json.dumps(self.payload, sort_keys=True, default=str)
        raw = f"{self.origin.name}:{self.intent.name}:{self.project}:{payload_repr}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def __lt__(self, other: "WorldMutation") -> bool:
        """For PriorityQueue ordering: lower priority value = higher urgency."""
        return self.priority.value < other.priority.value
