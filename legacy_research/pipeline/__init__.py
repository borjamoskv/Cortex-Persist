# [C5-REAL] Exergy-Maximized
"""CORTEX Pipeline - END-to-END Contracts & Types.

Defines the sovereign pipeline contracts that wire all CORTEX layers
into a deterministic flow: Ingress → Context → Plan → Execute → Persist → Egress.

Law Ω₀: All contracts are synthesizable (pure dataclasses, no runtime magic).
Law Ω₅: Zero prose padding in type definitions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeliveryType(Enum):
    """Where the pipeline result is delivered."""

    MCP = "mcp"  # MCP tool response
    FILE = "file"  # Write to filesystem
    WEBHOOK = "webhook"  # HTTP POST to external URL
    STDOUT = "stdout"  # CLI output
    MEMORY = "memory"  # Persist to CORTEX memory only (no external delivery)


class PipelineStage(Enum):
    """Stages in the E2E pipeline for telemetry and tracing."""

    INGRESS = "ingress"
    CONTEXT = "context"
    PLANNING = "planning"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    EGRESS = "egress"


class PipelineStatus(Enum):
    """Terminal states for a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CANCELLED = "cancelled"


@dataclass
class DeliveryTarget:
    """Typed delivery destination."""

    type: DeliveryType
    path: str | None = None  # For FILE type
    url: str | None = None  # For WEBHOOK type
    headers: dict[str, str] = field(default_factory=dict)  # For WEBHOOK
    format: str = "markdown"  # Output format: markdown, json, code


@dataclass
class PipelineRequest:
    """The E2E contract for a pipeline invocation.

    Everything CORTEX needs to execute a mission from intent to delivery.
    """

    intent: str  # Natural language or structured command
    context_hints: list[str] = field(default_factory=list)  # KI names, fact IDs for pre-fetch
    budget_limit_usd: float = 0.10  # Ω₃ ceiling
    delivery: DeliveryTarget = field(
        default_factory=lambda: DeliveryTarget(type=DeliveryType.STDOUT)
    )
    mission_id: str = field(default_factory=lambda: f"m-{uuid.uuid4().hex[:12]}")
    tenant_id: str = "default"
    priority: int = 1  # 0=critical, 1=normal, 2=low
    timeout_s: float = 120.0  # Max wall-clock seconds
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class StageTrace:
    """Telemetry record for a single pipeline stage."""

    stage: PipelineStage
    started_at: float
    ended_at: float
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.latency_ms == 0.0 and self.ended_at > self.started_at:
            self.latency_ms = (self.ended_at - self.started_at) * 1000


@dataclass
class ContextPacket:
    """Assembled context from all knowledge sources."""

    facts: list[dict[str, Any]] = field(default_factory=list)  # From FactStore
    knowledge_items: list[dict[str, Any]] = field(default_factory=list)  # From KI/SQLite-Vec
    embeddings_used: list[str] = field(default_factory=list)  # IDs of vectors consumed
    relevance_scores: dict[str, float] = field(default_factory=dict)
    total_tokens: int = 0


@dataclass
class PipelineResult:
    """The terminal output of an E2E pipeline run.

    Contains the result, provenance chain, cost accounting,
    and full stage-by-stage telemetry.
    """

    mission_id: str
    status: PipelineStatus
    output: Any = None  # Structured result
    error: str | None = None
    cost_usd: float = 0.0
    ledger_hash: str = ""  # SHA-256 provenance
    context_used: list[str] = field(default_factory=list)  # What KIs/facts were consumed
    agent_chain: list[str] = field(default_factory=list)  # Which agents executed
    stages: list[StageTrace] = field(default_factory=list)  # Full trace
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    @property
    def latency_ms(self) -> float:
        """Total pipeline wall-clock latency."""
        if self.completed_at > self.created_at:
            return (self.completed_at - self.created_at) * 1000
        return sum(s.latency_ms for s in self.stages)

    @property
    def total_tokens(self) -> int:
        return sum(s.tokens_in + s.tokens_out for s in self.stages)


__all__ = [
    "ContextPacket",
    "DeliveryTarget",
    "DeliveryType",
    "PipelineRequest",
    "PipelineResult",
    "PipelineStage",
    "PipelineStatus",
    "StageTrace",
]
