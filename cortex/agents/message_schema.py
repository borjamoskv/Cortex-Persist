from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    DEAD_LETTER = "dead_letter"


class MessageKind(str, Enum):
    TASK_REQUEST = "task.request"
    TASK_ACCEPTED = "task.accepted"
    TASK_PROGRESS = "task.progress"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    VERIFICATION_REQUEST = "verification.request"
    VERIFICATION_RESULT = "verification.result"
    SECURITY_SCAN_REQUEST = "security.scan.request"
    SECURITY_SCAN_RESULT = "security.scan.result"
    HANDOFF_REQUEST = "handoff.request"
    HANDOFF_RESULT = "handoff.result"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Old stuff for built-ins MVP backwards compatibility
    TASK_RESULT = "task.result"
    FACT_PROPOSAL = "fact.proposal"
    FACT_INVALIDATED = "fact.invalidated"
    ALERT_ENTROPY = "alert.entropy"
    HANDOFF_ACCEPTED = "handoff.accepted"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"


class AgentMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str
    causation_id: Optional[str] = None
    sender: str
    recipient: str
    kind: MessageKind
    payload: dict[str, Any] = Field(default_factory=dict)
    state: MessageState = MessageState.PENDING
    priority: int = 0
    ttl_seconds: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_context: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> AgentMessage:
        return cls.model_validate_json(raw)


def new_message(
    sender: str,
    recipient: str,
    kind: MessageKind,
    payload: dict[str, Any],
    *,
    correlation_id: str = "auto",
    causation_id: Optional[str] = None,
    ttl_seconds: int = 3600,
    priority: int = 0,
    trace_context: Optional[dict[str, Any]] = None,
) -> AgentMessage:
    if correlation_id == "auto":
        correlation_id = str(uuid4())
    return AgentMessage(
        sender=sender,
        recipient=recipient,
        kind=kind,
        payload=payload,
        correlation_id=correlation_id,
        causation_id=causation_id,
        ttl_seconds=ttl_seconds,
        priority=priority,
        trace_context=trace_context or {},
    )


MessageType = MessageKind
