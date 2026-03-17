"""
CORTEX v5.3 — Cognitive Memory Domain Models.

Tripartite Memory Architecture (KETER-∞ Frontera 2):
- MemoryEntry: Legacy L2 vector store payload (Qdrant-compatible).
- MemoryEvent: Pydantic v2 model for L1/L3 interaction events.
- EpisodicSnapshot: Pydantic v2 model for L2 compressed episodes.
- CortexFactModel: Zero-Trust L2 Vector Fact for CORTEX v6.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

try:
    from cortex.extensions.axioms.topological_id import flake_gen

    def next_id() -> str:
        return flake_gen.next_lexicographic_id()
except ImportError:
    import uuid

    def next_id() -> str:
        return uuid.uuid4().hex


def now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass()
class CausalEpisode:
    """A DAG of causally-linked facts forming a coherent temporal episode.

    Built by traversing `parent_decision_id` chains in the facts table.
    Enables the LLM to understand *why* something happened, not just *what*.
    """

    episode_id: str = field(default_factory=next_id)
    root_fact_id: int = 0
    fact_chain: list[dict] = field(default_factory=list)
    project: str = ""
    summary: str = ""
    depth: int = 0
    ghost_count: int = 0
    decision_count: int = 0
    created_at: float = field(default_factory=time.time)

    @property
    def entropy_density(self) -> float:
        """Ghost ratio within this episode (0.0 = clean, 1.0 = all ghosts)."""
        total = self.ghost_count + self.decision_count
        if total == 0:
            return 0.0
        return self.ghost_count / total


__all__ = [
    "CausalEpisode",
    "CortexFactModel",
    "EpisodicSnapshot",
    "MemoryEntry",
    "MemoryEvent",
]


# ─── Cognitive Stratification Configuration ──────────────────────────

COGNITIVE_LAYER = Literal[
    "working",  # Immediate thread context (L1)
    "episodic",  # Chronological interaction logs (L2)
    "semantic",  # Stable knowledge/fact vault (L2 - Default)
    "relationship",  # Inter-personal consistency patterns (L2/L3)
    "emotional",  # Empathetic resonance and vibe (L2/L3)
]


# ─── Legacy L2 Payload (Qdrant-compatible) ────────────────────────────


@dataclass()
class MemoryEntry:
    """Atomic unit of vector-stored memory.

    Each entry represents a piece of knowledge that can be
    recalled by semantic similarity, not just exact text match.
    """

    content: str
    id: str = field(default_factory=next_id)
    project: str | None = None
    source: str = "episodic"  # episodic | fact | reflection | ghost
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def to_payload(self) -> dict[str, Any]:
        """Convert to Qdrant-compatible payload dict."""
        return {
            "content": self.content,
            "project": self.project or "",
            "source": self.source,
            "created_at": self.created_at,
            **self.metadata,
        }


# ─── Source Monitoring & Metamemory Tracking ─────────────────────────


class SourceMetadata(BaseModel):
    """Tracks origin of the knowledge for Source Monitoring."""

    origin: Literal["user", "agent", "document", "system", "abstraction"] = Field(
        default="system", description="Where did this memory come from?"
    )
    author: str = Field(default="", description="Specific entity (e.g., username, agent_id).")
    document_ref: str = Field(default="", description="Reference to external source if any.")
    confidence_in_source: float = Field(
        default=1.0, description="Trust in the source itself [0, 1]."
    )


class MemoryAccessStats(BaseModel):
    """Metamemory statistics tracking retrieval and encoding health."""

    last_successful_retrieval: datetime | None = Field(
        default=None, description="UTC time of last hit."
    )
    retrieval_failure_count: int = Field(default=0, description="Consecutive or total failures.")
    total_access_count: int = Field(default=0, description="Total times this memory was recalled.")
    average_retrieval_latency_ms: float = Field(
        default=0.0, description="Average time to retrieve."
    )
    decay_predicted_date: datetime | None = Field(
        default=None, description="When will this be pruned?"
    )


# ─── Tripartite Memory Models (Pydantic v2) ──────────────────────────


class MemoryEvent(BaseModel):
    """Atomic unit of cognitive memory — an immutable interaction record.

    Stored in L3 (Event Ledger) for permanent audit trail.
    Flows through L1 (Working Memory) as the sliding window moves.
    """

    event_id: str = Field(
        default_factory=next_id,
        description="Unique identifier for this event.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of event creation.",
    )
    role: str = Field(description="Interaction role (user, assistant, system, tool).")
    content: str = Field(description="Raw content of the interaction.")
    token_count: int = Field(ge=0, description="Token count estimate.")
    session_id: str = Field(description="Session identifier linking related events.")
    tenant_id: str = Field(default="default", description="Tenant isolation identifier.")
    prev_hash: str = Field(default="", description="Hash of the previous event (hash-chain).")
    signature: str = Field(default="", description="Cryptographic signature of this event.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured metadata (tool calls, emotions, tags).",
    )


class EpisodicSnapshot(BaseModel):
    """Compressed memory episode stored in L2 (Vector Store).

    Created when events overflow from L1, summarized and embedded
    for semantic retrieval (RAG interno).
    """

    snapshot_id: str = Field(
        default_factory=next_id,
        description="Unique identifier for this episode.",
    )
    summary: str = Field(description="Compressed textual summary of the events.")
    vector_embedding: list[float] = Field(
        description="384-dim embedding vector (all-MiniLM-L6-v2).",
    )
    linked_events: list[str] = Field(
        default_factory=list,
        description="Event IDs from L3 compressed into this episode.",
    )
    session_id: str = Field(default="", description="Originating session.")
    tenant_id: str = Field(default="default", description="Tenant isolation identifier.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of snapshot creation.",
    )


class CortexFactModel(BaseModel):
    """Zero-Trust L2 Vector Fact for SQLite-vec in CORTEX v6.

    Designed to completely isolate facts per tenant while allowing
    cross-project bridges and OUROBOROS entropy tracking.
    """

    id: str = Field(
        default_factory=next_id,
        description="Unique identifier for the fact.",
    )
    tenant_id: str = Field(..., description="Absolute Zero-Trust Isolation.")
    project_id: str = Field(..., description="Originating project ID.")
    content: str = Field(..., description="Raw text content of the fact.")
    embedding: list[float] = Field(..., description="Vector embedding array.")
    timestamp: float = Field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp(),
        description="Unix timestamp of creation.",
    )

    # Stratified Memory (Inspiration: Letta RFC #3179)
    cognitive_layer: COGNITIVE_LAYER = Field(
        default="semantic", description="Target cognitive layer for this fact."
    )
    parent_decision_id: int | None = Field(
        default=None, description="Causal anchor to the parent decision."
    )

    # Sovereign Metadata
    is_diamond: bool = Field(default=False, description="Immune to temporal decay.")
    is_bridge: bool = Field(default=False, description="Pattern transferred between projects.")
    confidence: str = Field(default="C5", description="Confidence level [C1-C5].")

    # Entropy and Health (The OUROBOROS engine will update this)
    success_rate: float = Field(default=1.0, description="Degrades if this fact causes errors.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured metadata (session_id, tool calls, etc).",
    )
    specular_embedding: list[int] | None = Field(
        default=None,
        description="HDC Specular Memory (intent trace) bipolar hypervector.",
    )

    # Pragmatic Metamemory Phase 1 Additions
    source_metadata: SourceMetadata = Field(
        default_factory=SourceMetadata, description="Provenance of the fact for Source Monitoring."
    )
    access_stats: MemoryAccessStats = Field(
        default_factory=MemoryAccessStats, description="Metamemory usage stats."
    )

    @property
    def age_days(self) -> float:
        """Calculate fact age in days."""
        delta = datetime.now(timezone.utc).timestamp() - self.timestamp
        return max(0.0, delta / 86400.0)

    def update_on_read(self, latency_ms: float = 0.0) -> CortexFactModel:
        """Basic reconsolidation proxy: updates metamemory usage stats upon structural read."""
        stats = self.access_stats
        new_count = stats.total_access_count + 1
        new_avg = (
            stats.average_retrieval_latency_ms * stats.total_access_count + latency_ms
        ) / new_count
        new_stats = stats.model_copy(
            update={
                "last_successful_retrieval": datetime.now(timezone.utc),
                "total_access_count": new_count,
                "average_retrieval_latency_ms": round(new_avg, 2),
            }
        )
        return self.model_copy(update={"access_stats": new_stats})

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
