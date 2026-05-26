"""NEXUS — Pydantic models for the Sovereign Agent Directory.

Strict typing. No float for scores — Decimal would be ideal but
we use float with explicit rounding for V1 speed.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TrustTier(str, Enum):
    """Agent trust tiers derived from Bayesian posterior mean."""

    UNVERIFIED = "unverified"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    SOVEREIGN = "sovereign"


class AgentStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    SUSPENDED = "suspended"


class Capability(str, Enum):
    CODE = "code"
    SECURITY = "security"
    INTEL = "intel"
    DATA = "data"
    CREATIVE = "creative"
    MARKETING = "marketing"
    OSINT = "osint"
    INFRA = "infra"
    FINANCE = "finance"
    RESEARCH = "research"
    LEGAL = "legal"
    DESIGN = "design"


class TrustSignal(str, Enum):
    """Signals that update an agent's trust score."""

    VERIFY = "verify"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"
    REPORT = "report"
    VOUCH = "vouch"
    REVOKE = "revoke"


# ── Request Models ──────────────────────────────────────────────


class AgentRegistration(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    description: str = Field(default="", max_length=512)
    capabilities: list[Capability] = Field(default_factory=list)
    owner: str = Field(default="anonymous", max_length=128)
    website: str = Field(default="", max_length=256)


class TrustSignalRequest(BaseModel):
    signal: TrustSignal
    source_agent_id: str = Field(default="system")
    reason: str = Field(default="", max_length=256)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=256)
    description: str = Field(default="", max_length=2048)
    required_capabilities: list[Capability] = Field(default_factory=list)
    reward: float = Field(default=0.0, ge=0.0)
    delegator_id: str = Field(default="system")


# ── Response Models ─────────────────────────────────────────────


class TrustScore(BaseModel):
    tier: TrustTier
    posterior_mean: float
    alpha: float
    beta: float
    total_signals: int
    history: list[dict] = Field(default_factory=list)


class Agent(BaseModel):
    id: str
    name: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    owner: str = "anonymous"
    website: str = ""
    status: AgentStatus = AgentStatus.OFFLINE
    trust: TrustScore
    public_key: str = ""
    registered_at: str = ""
    last_seen: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0
    avatar_seed: str = ""  # deterministic avatar generation


class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    required_capabilities: list[str] = Field(default_factory=list)
    status: str = "open"  # open, assigned, completed, failed
    delegator_id: str = "system"
    assignee_id: str | None = None
    reward: float = 0.0
    created_at: str = ""
    completed_at: str | None = None


class ActivityEvent(BaseModel):
    id: str
    event_type: str  # registration, verification, task_complete, vouch, etc.
    agent_id: str
    agent_name: str
    target_id: str | None = None
    target_name: str | None = None
    description: str = ""
    timestamp: str = ""


class DirectoryStats(BaseModel):
    total_agents: int = 0
    verified_agents: int = 0
    online_agents: int = 0
    total_tasks: int = 0
    tasks_completed: int = 0
    avg_trust_score: float = 0.0
