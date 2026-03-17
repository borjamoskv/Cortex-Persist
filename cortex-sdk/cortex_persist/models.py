"""
SORTU-Ω Core Types & Models

This module defines the canonical types for the SORTU-Ω public SDK.
It includes trust semantics, query models, operational results, health reports,
and event envelopes, strictly adhering to the v0.2 RFC specifications.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, TypedDict

# ─── Trust Semantics Enums ─────────────────────────────────────────────

<<<<<<< HEAD

=======
>>>>>>> origin/main
class EvidenceLevel(str, Enum):
    NONE = "none"
    BASIC = "basic"
    TRACEABLE = "traceable"
    VERIFIED = "verified"

<<<<<<< HEAD

class TrustGrade(str, Enum):
    A = "A"  # Verified, strict policy, high integrity
    B = "B"  # Traceable, standard policy
    C = "C"  # Basic provenance, some warnings
    D = "D"  # Degraded constraints
    F = "F"  # Untrusted or tainted

=======
class TrustGrade(str, Enum):
    A = "A" # Verified, strict policy, high integrity
    B = "B" # Traceable, standard policy
    C = "C" # Basic provenance, some warnings
    D = "D" # Degraded constraints
    F = "F" # Untrusted or tainted
>>>>>>> origin/main

class IntegrityState(str, Enum):
    UNKNOWN = "unknown"
    PARTIAL = "partial"
    VERIFIED = "verified"
    FAILED = "failed"
    STALE = "stale"

<<<<<<< HEAD

=======
>>>>>>> origin/main
class TaintState(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"

<<<<<<< HEAD

# ─── Core Types ────────────────────────────────────────────────────────


@dataclass
class EvidenceItem:
    """A single piece of evidence from the memory layer."""

=======
# ─── Core Types ────────────────────────────────────────────────────────

@dataclass
class EvidenceItem:
    """A single piece of evidence from the memory layer."""
>>>>>>> origin/main
    id: str
    project: str
    content: str
    fact_type: str
    tags: list[str]
    created_at: str
    valid_from: str
    valid_until: str | None
    source_uri: str
    confidence: float
    evidence_level: EvidenceLevel
    integrity: IntegrityState
    taint: TaintState
    is_tombstoned: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

<<<<<<< HEAD

# ─── Query Semantics ───────────────────────────────────────────────────


class QueryInput(TypedDict, total=False):
    """Input parameters for a memory query."""

=======
# ─── Query Semantics ───────────────────────────────────────────────────

class QueryInput(TypedDict, total=False):
    """Input parameters for a memory query."""
>>>>>>> origin/main
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

<<<<<<< HEAD

@dataclass
class QueryEvidenceLevel:
    """The aggregate evidence level for a query result."""

=======
@dataclass
class QueryEvidenceLevel:
    """The aggregate evidence level for a query result."""
>>>>>>> origin/main
    level: EvidenceLevel
    grade: TrustGrade
    verification_proof: str | None = None

<<<<<<< HEAD

@dataclass
class QueryPlan:
    """The execution plan and warnings for a query."""

=======
@dataclass
class QueryPlan:
    """The execution plan and warnings for a query."""
>>>>>>> origin/main
    routing_strategy: str
    execution_time_ms: float
    degraded: bool
    warnings: list[str] = field(default_factory=list)

<<<<<<< HEAD

@dataclass
class QueryResult:
    """The result of a memory query operation."""

=======
@dataclass
class QueryResult:
    """The result of a memory query operation."""
>>>>>>> origin/main
    items: list[EvidenceItem]
    evidence: QueryEvidenceLevel
    plan: QueryPlan

<<<<<<< HEAD

# ─── Operational Results ───────────────────────────────────────────────


class AcceptanceResult(TypedDict):
    """Successful operation result."""

=======
# ─── Operational Results ───────────────────────────────────────────────

class AcceptanceResult(TypedDict):
    """Successful operation result."""
>>>>>>> origin/main
    accepted: Literal[True]
    operation_id: str
    warnings: list[str]

<<<<<<< HEAD

=======
>>>>>>> origin/main
class RejectionResult(TypedDict):
    """
    Governance rejection.
    The system understood the request, but policy or safety rules denied it.
    """
<<<<<<< HEAD

=======
>>>>>>> origin/main
    accepted: Literal[False]
    code: str
    message: str
    layer: Literal["guard", "membrane", "policy", "verification"]
    rule_id: str
    severity: Literal["low", "medium", "high", "critical"]
    evidence: list[dict[str, Any]]
    remediation: list[str]

<<<<<<< HEAD

=======
>>>>>>> origin/main
class FailureResult(TypedDict):
    """
    Operational failure.
    The system attempted to execute but failed due to external or internal limits.
    """
<<<<<<< HEAD

=======
>>>>>>> origin/main
    status: Literal["failed"]
    reason: str
    code: str  # Must be from ERROR-CODE-REGISTRY
    category: Literal["dependency", "storage", "runtime", "capability"]
    is_retryable: bool
    failed_at: str
    retry_after_ms: int | None

<<<<<<< HEAD

=======
>>>>>>> origin/main
OperationResult = AcceptanceResult | RejectionResult | FailureResult

# ─── Runtime & Identity ────────────────────────────────────────────────

<<<<<<< HEAD

@dataclass
class CapabilityReport:
    """Report of a specific agent capability."""

=======
@dataclass
class CapabilityReport:
    """Report of a specific agent capability."""
>>>>>>> origin/main
    name: str
    status: Literal["active", "degraded", "offline"]
    latency_ms: float
    error_rate: float
    last_verified: str

<<<<<<< HEAD

class HealthReport(TypedDict):
    """Overall system health and capability report."""

=======
class HealthReport(TypedDict):
    """Overall system health and capability report."""
>>>>>>> origin/main
    status: Literal["ok", "degraded", "blocked"]
    components: dict[str, str]
    degraded_features: list[str]
    warnings: list[str]

<<<<<<< HEAD

@dataclass
class RecoveryReport:
    """Report of the agent's memory recovery status during boot."""

=======
@dataclass
class RecoveryReport:
    """Report of the agent's memory recovery status during boot."""
>>>>>>> origin/main
    status: Literal["clean", "recovered", "failed"]
    recovered_items: int
    failed_items: int
    last_checkpoint_id: str | None = None
    warnings: list[str] = field(default_factory=list)

<<<<<<< HEAD

# ─── Coordination (Events) ─────────────────────────────────────────────


@dataclass
class EventEnvelope:
    """Canonical event envelope for SORTU-Ω coordination."""

=======
# ─── Coordination (Events) ─────────────────────────────────────────────

@dataclass
class EventEnvelope:
    """Canonical event envelope for SORTU-Ω coordination."""
>>>>>>> origin/main
    event_id: str
    event_type: str
    api_version: str
    timestamp: str
    issuer: str
    tenant_id: str
    payload: dict[str, Any]
    causality_id: str | None = None
    signature: str | None = None
