from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TaskRequestPayload(BaseModel):
    task_id: str
    objective: str
    input: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)


class ToolCallPayload(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultPayload(BaseModel):
    tool_name: str
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class VerificationRequestPayload(BaseModel):
    subject: Literal["tool_result", "task_result", "plan_step"]
    candidate: dict[str, Any]


class VerificationResultPayload(BaseModel):
    ok: bool
    verdict: Literal["accepted", "rejected", "needs_handoff"]
    reasons: list[str] = Field(default_factory=list)


class TaskCompletedPayload(BaseModel):
    task_id: str
    output: dict[str, Any] = Field(default_factory=dict)


class TaskFailedPayload(BaseModel):
    task_id: str
    error: str
    retryable: bool = False
