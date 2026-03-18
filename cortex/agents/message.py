"""CORTEX Agent Runtime — Typed Message Protocol.

All inter-agent communication flows through AgentMessage.
MessageKind enforces a finite vocabulary of interactions.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class MessageKind(str, Enum):
    """Finite vocabulary of inter-agent message types."""

    TASK_REQUEST = "task.request"
    TASK_ACCEPTED = "task.accepted"
    TASK_PROGRESS = "task.progress"
    TASK_RESULT = "task.result"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    VERIFICATION_REQUEST = "verification.request"
    VERIFICATION_RESULT = "verification.result"
    SECURITY_SCAN_REQUEST = "security.scan.request"
    SECURITY_SCAN_RESULT = "security.scan.result"

    FACT_PROPOSAL = "fact.proposal"
    FACT_INVALIDATED = "fact.invalidated"
    ALERT_ENTROPY = "alert.entropy"
    HANDOFF_REQUEST = "handoff.request"
    HANDOFF_ACCEPTED = "handoff.accepted"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"


@dataclass()
class AgentMessage:
    """Typed message for inter-agent communication."""

    message_id: str
    sender: str
    recipient: str
    kind: MessageKind
    payload: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    correlation_id: str | None = None
    causation_id: str | None = None
    ttl: int = 3600
    priority: int = 0
    trace_context: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON for transport."""
        return json.dumps(
            {
                "message_id": self.message_id,
                "sender": self.sender,
                "recipient": self.recipient,
                "kind": self.kind.value,
                "payload": self.payload,
                "created_at": self.created_at,
                "correlation_id": self.correlation_id,
                "causation_id": self.causation_id,
                "ttl": self.ttl,
                "priority": self.priority,
                "trace_context": self.trace_context,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, raw: str) -> AgentMessage:
        """Deserialize from JSON."""
        data = json.loads(raw)
        return cls(
            message_id=data["message_id"],
            sender=data["sender"],
            recipient=data["recipient"],
            kind=MessageKind(data["kind"]),
            payload=data["payload"],
            created_at=data.get("created_at", time.time()),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            ttl=data.get("ttl", 3600),
            priority=data.get("priority", 0),
            trace_context=data.get("trace_context", {}),
        )


def new_message(
    sender: str,
    recipient: str,
    kind: MessageKind,
    payload: dict[str, Any],
    *,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    ttl: int = 3600,
    priority: int = 0,
    trace_context: dict[str, Any] | None = None,
) -> AgentMessage:
    """Factory for creating new messages with auto-generated IDs."""
    return AgentMessage(
        message_id=str(uuid4()),
        sender=sender,
        recipient=recipient,
        kind=kind,
        payload=payload,
        correlation_id=correlation_id,
        causation_id=causation_id,
        ttl=ttl,
        priority=priority,
        trace_context=trace_context or {},
    )
