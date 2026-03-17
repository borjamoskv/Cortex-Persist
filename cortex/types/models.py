"""
CORTEX v5.0 — API Models.
Centralized Pydantic models for request/response validation.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "AcceptanceResult",
    "AgentRegisterRequest",
    "AgentResponse",
    "ApiKeyListItem",
    "ApiKeyResponse",
    "CheckpointResponse",
    "ContextSignalModel",
    "ContextSnapshotResponse",
    "DeepHealthResponse",
    "EventEnvelope",
    "ExportResponse",
    "FactResponse",
    "GateActionResponse",
    "GateApprovalRequest",
    "GateStatusResponse",
    "HealthCheckDetail",
    "HealthReport",
    "HeartbeatRequest",
    "LedgerReportResponse",
    "MejoraloScanRequest",
    "MejoraloScanResponse",
    "MejoraloSessionRequest",
    "MejoraloSessionResponse",
    "MejoraloShipRequest",
    "MejoraloShipResponse",
    "MissionLaunchRequest",
    "MissionResponse",
    "OperationResult",
    "ProjectScoreModel",
    "QueryEvidenceLevel",
    "QueryInput",
    "QueryResultData",
    "RejectionResult",
    "SearchRequest",
    "SearchResult",
    "ShipSealModel",
    "StatusResponse",
    "StoreRequest",
    "StoreResponse",
    "TimeSummaryResponse",
    "TraceInput",
    "VoteRequest",
    "VoteResponse",
    "VoteV2Request",
]


# ─── SDK Surface v0.2 Protocol Types ─────────────────────────────────

QueryIntent = Literal["lookup", "explore", "audit"]
QueryStrategy = Literal["auto", "text", "vector", "hybrid", "temporal", "graph"]


class QueryInput(TypedDict, total=False):
    tenant_id: str
    project: str
    query: str
    strategy: Literal["auto", "bayesian", "hybrid", "text", "vector", "temporal", "graph"]
    as_of: str
    top_k: int
    min_confidence: float
    include_graph: bool
    include_history: bool
    include_taint: bool


class QueryEvidenceLevel(BaseModel):
    level: Literal["none", "basic", "traceable", "verified"]
    reason: str


class QueryResultData(BaseModel):
    answer: Optional[str] = None
    evidence_level: Optional[QueryEvidenceLevel] = None
    degraded: bool = False
    degraded_reason: Optional[str] = None
    trace: Optional[dict] = None
    facts: Optional[list[dict]] = None


class RejectionResult(TypedDict):
    accepted: Literal[False]
    code: str
    message: str
    layer: Literal["guard", "membrane", "policy", "verification"]
    rule_id: str
    severity: Literal["low", "medium", "high", "critical"]
    evidence: list[dict]
    remediation: list[str]


class AcceptanceResult(TypedDict):
    accepted: Literal[True]
    operation_id: str
    warnings: list[str]


OperationResult = AcceptanceResult | RejectionResult


class TraceInput(BaseModel):
    tx_id: Optional[str] = None
    fact_id: Optional[str] = None
    decision_id: Optional[str] = None
    query_result_id: Optional[str] = None
    depth: int = Field(5, ge=1, le=20)


class EventEnvelope(BaseModel):
    schema_version: str = "1.0"
    event_id: str
    event_type: str
    ts: str
    tenant_id: str
    project: str
    source: str
    sequence: int
    idempotency_key: str
    payload: dict


class StoreRequest(BaseModel):
    project: str = Field(..., max_length=100, description="Project/namespace for the fact")
    content: str = Field(..., max_length=50000, description="The fact content")
    fact_type: str = Field(
        "knowledge", max_length=20, description="Type: knowledge, decision, mistake, bridge, ghost"
    )
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    source: str = Field("", max_length=200, description="Origin of the fact (e.g. agent:vex)")
    meta: Optional[dict] = Field(None, description="Optional JSON metadata")

    @field_validator("project", "content")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Must not be empty or whitespace only")
        return v


class StoreResponse(BaseModel):
    fact_id: int
    project: str
    message: str


class SearchRequest(BaseModel):
    query: str = Field(..., max_length=1024, description="Natural language search query")
    k: int = Field(5, ge=1, le=50, description="Number of results")
    project: Optional[str] = Field(None, max_length=100, description="Filter by project")
    as_of: Optional[str] = Field(None, description="Temporal filter (ISO 8601)")
    fact_type: Optional[str] = Field(None, description="Filter by fact type")
    tags: Optional[list[str]] = Field(None, description="Filter by tags")
    graph_depth: int = Field(
        0, ge=0, le=5, description="Enable Graph-RAG (0=off, >0=depth of context traversal)"
    )
    include_graph: bool = Field(
        False, description="Include the localized context subgraph in response"
    )

    @field_validator("query")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Must not be empty or whitespace only")
        return v


class SearchResult(BaseModel):
    fact_id: int
    project: str
    content: str
    fact_type: str
    score: float
    tags: list[str]
    created_at: str
    updated_at: str
    meta: Optional[dict] = None
    hash: Optional[str] = None
    context: Optional[dict] = Field(
        None, description="Graph-RAG context (subgraph or related entities)"
    )


class VoteRequest(BaseModel):
    value: int = Field(..., description="1 to verify, -1 to dispute, 0 to remove")

    @field_validator("value")
    @classmethod
    def valid_vote(cls, v: int) -> int:
        if v not in (1, -1, 0):
            raise ValueError("Vote must be 1, -1, or 0")
        return v


class VoteResponse(BaseModel):
    fact_id: int
    agent: str
    vote: int
    new_consensus_score: float
    confidence: Optional[str | float] = None
    status: str = "recorded"


class AgentRegisterRequest(BaseModel):
    name: str = Field(..., max_length=100)
    agent_type: str = Field("ai", description="ai, human, oracle, system")
    public_key: str = Field("", description="Optional Ed25519 public key")


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    agent_type: str
    reputation_score: float
    created_at: str


class VoteV2Request(BaseModel):
    agent_id: str = Field(..., description="UUID of the registered agent")
    vote: int = Field(..., description="1 to verify, -1 to dispute, 0 to remove")
    reason: Optional[str] = Field(None, max_length=500)
    signature: Optional[str] = Field(None, description="Optional cryptographic signature")


class FactResponse(BaseModel):
    id: int
    project: str
    content: str
    fact_type: str
    tags: list[str]
    created_at: str
    updated_at: str
    confidence: Optional[str | float] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    source: Optional[str] = None
    meta: Optional[dict] = None
    is_tombstoned: bool = False
    hash: Optional[str] = None
    tx_id: Optional[str] = None
    consensus_score: Optional[float] = None


class StatusResponse(BaseModel):
    version: str
    total_facts: int
    active_facts: int
    deprecated: int
    projects: int
    embeddings: int
    transactions: int
    db_size_mb: float


class ExportResponse(BaseModel):
    """Response for project memory export."""

    status: str = "success"
    project: str
    artifact: str
    message: str


class HealthReport(TypedDict):
    status: Literal["ok", "degraded", "blocked"]
    components: dict[str, str]
    degraded_features: list[str]
    warnings: list[str]


class RecoveryReport(BaseModel):
    """Report of the agent's memory recovery status during boot."""

    status: Literal["clean", "recovered", "failed"]
    recovered_items: int
    failed_items: int
    last_checkpoint_id: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class HealthCheckDetail(BaseModel):
    """Single health probe result."""

    status: str
    detail: Optional[str] = None
    version: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    pending_uncheckpointed: Optional[int] = None
    last_checkpoint_tx: Optional[int] = None
    active_connections: Optional[int] = None
    max_connections: Optional[int] = None
    utilization: Optional[str] = None
    useful_facts_ratio: Optional[float] = None
    duplicates_ratio: Optional[float] = None
    total_facts: Optional[int] = None

    model_config = {"extra": "allow"}


class DeepHealthResponse(BaseModel):
    """Structured deep health check response."""

    status: str  # "healthy" | "degraded"
    version: str
    schema_version: str
    checks: dict[str, HealthCheckDetail]
    latency_ms: float

    # V8 Evaluation Metrics
    p95_latency_ms: Optional[float] = Field(
        default=None, description="p95 latency of ambient context boot"
    )
    stale_ratio: Optional[float] = Field(
        default=None, description="Ratio of facts older than 180 days with no hits"
    )


class ApiKeyResponse(BaseModel):
    """Response after creating an API key."""

    key: str
    name: str
    prefix: str
    tenant_id: str
    message: str


class ApiKeyListItem(BaseModel):
    """Non-sensitive API key metadata."""

    id: str
    name: str
    prefix: str
    tenant_id: str
    permissions: list[str]
    is_active: bool
    created_at: str
    last_used: Optional[str] = None


class HeartbeatRequest(BaseModel):
    project: str = Field(..., max_length=100)
    entity: str = Field("", max_length=1024)
    category: Optional[str] = Field(None, max_length=50)
    branch: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=50)
    meta: Optional[dict] = None


class TimeSummaryResponse(BaseModel):
    total_seconds: int
    total_hours: float
    by_category: dict[str, int]
    by_project: dict[str, int]
    entries: int
    heartbeats: int
    top_entities: list[list]  # [[entity, count], ...]


# ─── Mission Models ──────────────────────────────────────────────────


class MissionLaunchRequest(BaseModel):
    project: str = Field(..., max_length=100)
    goal: str = Field(..., max_length=2000)
    formation: str = "IRON_DOME"
    agents: int = Field(10, ge=1, le=50)


class MissionResponse(BaseModel):
    intent_id: int
    result_id: Optional[int] = None
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class LedgerReportResponse(BaseModel):
    valid: bool
    violations: list[dict[str, Any]]
    tx_checked: int = 0
    roots_checked: int = 0
    votes_checked: int = 0
    vote_checkpoints_checked: int = 0


class CheckpointResponse(BaseModel):
    checkpoint_id: Optional[int]
    message: str
    status: str = "success"


# ─── MEJORAlo Models ────────────────────────────────────────────────


class MejoraloScanRequest(BaseModel):
    project: str = Field(..., max_length=100)
    path: str = Field(..., description="Ruta al directorio del proyecto")
    deep: bool = Field(False, description="Activa dimensión Psi + análisis profundo")


class DimensionResultModel(BaseModel):
    name: str
    score: int = Field(..., ge=0, le=100)
    weight: str
    findings: list[str] = Field(default_factory=list)


class MejoraloScanResponse(BaseModel):
    project: str
    score: int
    stack: str
    dimensions: list[DimensionResultModel]
    dead_code: bool
    total_files: int = 0
    total_loc: int = 0
    fact_id: Optional[int] = None


class MejoraloSessionRequest(BaseModel):
    project: str = Field(..., max_length=100)
    score_before: int = Field(..., ge=0, le=100)
    score_after: int = Field(..., ge=0, le=100)
    actions: list[str] = Field(default_factory=list)


class MejoraloSessionResponse(BaseModel):
    fact_id: int
    project: str
    delta: int
    status: str = "recorded"


class MejoraloShipRequest(BaseModel):
    project: str = Field(..., max_length=100)
    path: str = Field(..., description="Ruta al directorio del proyecto")


class ShipSealModel(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class MejoraloShipResponse(BaseModel):
    project: str
    ready: bool
    seals: list[ShipSealModel]
    passed: int
    total: int = 7


# ─── SovereignGate Models ────────────────────────────────────────────


class GateApprovalRequest(BaseModel):
    signature: str = Field(..., description="HMAC-SHA256 signature of the challenge")
    operator_id: Optional[str] = Field(None, description="Operator identifier")


class GateActionResponse(BaseModel):
    action_id: str
    level: str
    description: str
    command: Optional[list[str]] = None
    project: Optional[str] = None
    status: str
    created_at: str
    approved_at: Optional[str] = None
    operator_id: Optional[str] = None


class GateStatusResponse(BaseModel):
    policy: str
    timeout_seconds: int
    pending: int = 0
    approved: int = 0
    denied: int = 0
    expired: int = 0
    executed: int = 0
    total_audit_entries: int = 0


# ─── Context Engine Models ───────────────────────────────────────────


class ContextSignalModel(BaseModel):
    source: str
    signal_type: str
    content: str
    project: Optional[str] = None
    timestamp: str
    weight: float


class ProjectScoreModel(BaseModel):
    project: str
    score: float


class ContextSnapshotResponse(BaseModel):
    active_project: Optional[str] = None
    confidence: str
    signals_used: int
    summary: str
    top_signals: list[ContextSignalModel] = Field(default_factory=list)
    projects_ranked: list[ProjectScoreModel] = Field(default_factory=list)
