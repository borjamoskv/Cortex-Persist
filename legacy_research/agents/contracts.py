# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


from uuid import uuid4

class TaskRequestPayload(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    objective: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    op: str | None = None
    code: str | None = None


class ToolCallPayload(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultPayload(BaseModel):
    tool_name: str
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class VerificationRequestPayload(BaseModel):
    subject: Literal["tool_result", "task_result", "plan_step"]
    candidate: dict[str, Any]


class VerificationResultPayload(BaseModel):
    ok: bool
    verdict: Literal["accepted", "rejected", "needs_handoff"]
    reasons: list[str] = Field(default_factory=list)


class HandoffRequestPayload(BaseModel):
    reason: str = ""
    causal_gap: str = ""
    required_capability: str = ""
    confidence: float = 1.0
    handoff: dict[str, Any] | None = None


class TaskCompletedPayload(BaseModel):
    task_id: str
    output: dict[str, Any] = Field(default_factory=dict)


class TaskFailedPayload(BaseModel):
    task_id: str
    error: str
    error_state: Literal["transient", "validation", "permanent"] = "permanent"
    retryable: bool = False

