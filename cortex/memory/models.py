"""
CORTEX v5.3 — Cognitive Memory Domain Models.

Tripartite Memory Architecture (KETER-∞ Frontera 2):
- MemoryEntry: Legacy L2 vector store payload (Qdrant-compatible).
- MemoryEvent: Pydantic v2 model for L1/L3 interaction events.
- EpisodicSnapshot: Pydantic v2 model for L2 compressed episodes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from cortex.temporal import now_iso

__all__ = ["EpisodicSnapshot", "MemoryEntry", "MemoryEvent"]


# ─── Legacy L2 Payload (Qdrant-compatible) ────────────────────────────


@dataclass(slots=True)
class MemoryEntry:
    """Atomic unit of vector-stored memory.

    Each entry represents a piece of knowledge that can be
    recalled by semantic similarity, not just exact text match.
    """

    content: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
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


# ─── Tripartite Memory Models (Pydantic v2) ──────────────────────────


class MemoryEvent(BaseModel):
    """Atomic unit of cognitive memory — an immutable interaction record.

    Stored in L3 (Event Ledger) for permanent audit trail.
    Flows through L1 (Working Memory) as the sliding window moves.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
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
        default_factory=lambda: str(uuid.uuid4()),
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of snapshot creation.",
    )
