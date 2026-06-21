from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

TaskKind = Literal["reason", "retrieve", "plan", "execute", "audit", "summarize", "memory"]


class AgentCapabilityModel(BaseModel):
    name: str = Field(..., max_length=100)
    kinds: list[TaskKind] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    priority: int = 0
    max_concurrent: int = 1


class AgentRegisterRequestV2(BaseModel):
    name: str = Field(..., max_length=100)
    agent_type: str = Field("ai", description="ai, human, oracle, system")
    public_key: str = Field("", description="Optional Ed25519 public key")
    capabilities: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class SubagentRequestModel(BaseModel):
    task_id: str
    kind: TaskKind
    target_agent: str = ""
    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)
    parent_task_id: Optional[str] = None
    timeout_ms: int = 30_000
    max_retries: int = 1
    require_capability: Optional[str] = None


class SubagentResponseModel(BaseModel):
    task_id: str
    ok: bool
    target_agent: str
    output: Any = None
    error: Optional[str] = None
    trace: dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None
