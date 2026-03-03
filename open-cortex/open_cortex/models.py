"""Open CORTEX — Pydantic models for the LLM-memory contract.

All request/response schemas for the 6 core endpoints:
plan, recall, write, justify, reconsolidate, audit.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ────────────────────────────────────────────────────────────


class Namespace(StrEnum):
    USER = "user"
    TEAM = "team"
    GLOBAL = "global"


class SourceType(StrEnum):
    USER = "user"
    AGENT = "agent"
    DOCUMENT = "document"
    SYSTEM = "system"
    ABSTRACTION = "abstraction"


class EdgeType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"


class ProvenanceMethod(StrEnum):
    EXTRACTION = "extraction"
    INFERENCE = "inference"
    USER_INPUT = "user_input"
    RECONSOLIDATION = "reconsolidation"


# ─── Core Memory Model ───────────────────────────────────────────────


def _mem_id() -> str:
    return f"mem_{uuid.uuid4().hex[:12]}"


def _now() -> datetime:
    return datetime.now(UTC)


class Provenance(BaseModel):
    """Tracks origin of the knowledge (Source Monitoring)."""

    source: SourceType = SourceType.SYSTEM
    method: ProvenanceMethod = ProvenanceMethod.USER_INPUT
    author: str = ""
    document_ref: str = ""
    created_by: str = ""
    created_at: datetime = Field(default_factory=_now)


class Belief(BaseModel):
    """Epistemic state of the memory."""

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    last_verified: datetime = Field(default_factory=_now)
    calibration_source: str = ""


class Freshness(BaseModel):
    """Temporal validity of the claim."""

    valid_from: datetime = Field(default_factory=_now)
    valid_until: datetime | None = None
    is_canonical: bool = True
    staleness_score: float = 0.0


class Version(BaseModel):
    """Lineage tracking for reconsolidation."""

    v: int = 1
    parent_id: str | None = None
    lineage: list[str] = Field(default_factory=list)


class Relation(BaseModel):
    """Edge between two memories."""

    type: EdgeType
    target_id: str
    reason: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Memory(BaseModel):
    """The atomic unit of the Open CORTEX standard."""

    id: str = Field(default_factory=_mem_id)
    content: str
    timestamp: datetime = Field(default_factory=_now)
    tags: list[str] = Field(default_factory=list)
    namespace: Namespace = Namespace.GLOBAL
    provenance: Provenance = Field(default_factory=Provenance)
    belief: Belief = Field(default_factory=Belief)
    freshness: Freshness = Field(default_factory=Freshness)
    version: Version = Field(default_factory=Version)
    relations: list[Relation] = Field(default_factory=list)
    embedding: list[float] | None = None
    pii: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


# ─── Plan Request / Response ─────────────────────────────────────────


class PlanStep(BaseModel):
    """A single step in the retrieval plan."""

    action: str = "recall"  # "recall" | "verify"
    filters: dict[str, Any] = Field(default_factory=dict)
    k: int = 5
    threshold: float | None = None


class Metamemory(BaseModel):
    """LLM's self-assessed epistemic state."""

    jol_expected: float = Field(default=0.5, ge=0.0, le=1.0)
    fok_estimate: float = Field(default=0.5, ge=0.0, le=1.0)
    force_recall: bool = False


class PlanRequest(BaseModel):
    """POST /plan — LLM generates a retrieval plan."""

    query: str
    turn_id: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    """Response from /plan."""

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    query_decomposition: list[PlanStep] = Field(default_factory=list)
    metamemory: Metamemory = Field(default_factory=Metamemory)
    rationale: str = ""


# ─── Recall Request / Response ───────────────────────────────────────


class RecallQuery(BaseModel):
    """A single search sub-query."""

    text: str
    k: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)
    canonical_only: bool = True


class RecallRequest(BaseModel):
    """POST /recall — Execute hybrid search."""

    plan_id: str
    queries: list[RecallQuery]
    search_strategy: str = "hybrid"  # "bm25" | "ann" | "hybrid"


class RecalledMemory(BaseModel):
    """A single memory chunk returned from recall."""

    memory_id: str
    content: str
    confidence: float
    freshness_days: int = 0
    source: str = ""
    relevance_score: float = 0.0
    retrieval_method: str = "hybrid"
    is_canonical: bool = True
    superseded_by: str | None = None
    tags: list[str] = Field(default_factory=list)


class RecallMetamemory(BaseModel):
    """Post-recall metamemory assessment."""

    fok_actual: float = 0.0
    coverage: float = 0.0
    contradiction_detected: bool = False
    contradiction_resolved: bool = False
    resolution: str = ""


class RecallResponse(BaseModel):
    """Response from /recall."""

    plan_id: str
    results: list[RecalledMemory] = Field(default_factory=list)
    metamemory: RecallMetamemory = Field(default_factory=RecallMetamemory)


# ─── Write Request / Response ────────────────────────────────────────


class WriteRequest(BaseModel):
    """POST /write — Store a new memory."""

    content: str
    tags: list[str] = Field(default_factory=list)
    namespace: Namespace = Namespace.GLOBAL
    source: SourceType = SourceType.SYSTEM
    method: ProvenanceMethod = ProvenanceMethod.USER_INPUT
    author: str = ""
    document_ref: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    valid_from: datetime | None = None
    relations: list[Relation] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class WriteResponse(BaseModel):
    """Response from /write."""

    id: str
    version: int = 1
    is_canonical: bool = True
    belief: Belief
    edges_created: int = 0


# ─── Justify Request / Response ──────────────────────────────────────


class Citation(BaseModel):
    """A single citation from memory."""

    memory_id: str
    excerpt: str = ""
    usage: str = "primary_evidence"


class IgnoredMemory(BaseModel):
    """A recalled memory that was not used."""

    memory_id: str
    reason: str = ""


class MemoryUseReport(BaseModel):
    """The LLM's self-report of memory usage."""

    used_memories: list[Citation] = Field(default_factory=list)
    ignored_memories: list[IgnoredMemory] = Field(default_factory=list)
    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    plan_adherence: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_output: float = Field(default=0.5, ge=0.0, le=1.0)


class JustifyRequest(BaseModel):
    """POST /justify — Response with citations."""

    plan_id: str
    answer: str
    memory_use_report: MemoryUseReport


class JustifyResponse(BaseModel):
    """Response from /justify — acknowledgment + computed metrics."""

    plan_id: str
    metrics: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


# ─── Reconsolidate Request / Response ────────────────────────────────


class EvidenceItem(BaseModel):
    """External evidence supporting reconsolidation."""

    type: str = "document"
    ref: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ReconsolidateRequest(BaseModel):
    """POST /reconsolidate — Versioned truth update."""

    target_id: str
    action: str = "supersede"  # "supersede" | "contradict" | "update_confidence"
    new_content: str = ""
    tags: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    reason: str = ""


class ReconsolidateResponse(BaseModel):
    """Response from /reconsolidate."""

    new_memory_id: str
    superseded_id: str
    edge_type: EdgeType = EdgeType.SUPERSEDES
    old_canonical: bool = False
    new_canonical: bool = True
    audit_entry_id: int = 0


# ─── Audit Response ─────────────────────────────────────────────────


class AuditEntry(BaseModel):
    """A single entry in the audit trail."""

    action: str
    actor: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class AuditResponse(BaseModel):
    """GET /audit/{memory_id}."""

    memory_id: str
    current_state: dict[str, Any] = Field(default_factory=dict)
    history: list[AuditEntry] = Field(default_factory=list)
    edges: list[Relation] = Field(default_factory=list)
    version_chain: list[str] = Field(default_factory=list)
