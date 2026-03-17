# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Hypervisor — BeliefObject Contract.

Immutable cognitive units for the Belief Layer. The BeliefObject is the
unifying atom between the quad-model Cognitive Handoff:

  - Architect (GPT-5.4): designs schemas, contracts, RFCs
  - Auditor Premium (Claude Opus 4.6): high-severity contradiction detection
  - Auditor Economic (Gemini 2.5 Pro Deep Think): routine belief audit
  - Infrastructure (Gemini 3.1 Pro): episodic reads, prescreen

Design decision (C4🔵): Python dataclasses over Protobuf.
The project's serialization boundary is SQLite (local) + JSON (REST API).
Protobuf adds protoc build step for a single contract — disproportionate cost.
Migration path: @dataclass_to_proto adapter if cross-language federation arrives.
"""

from __future__ import annotations
from typing import Optional

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

__all__ = [
    "BeliefObject",
    "BeliefConfidence",
    "BeliefStatus",
    "BeliefVerdict",
    "ProvenanceChain",
    "ProvenanceEntry",
]


# ─── Enums ──────────────────────────────────────────────────────────────────


class BeliefConfidence(str, Enum):
    """Epistemic confidence level — maps to CORTEX C1→C5 scale."""

    C1_HYPOTHESIS = "C1"
    """Unverified conjecture — single source, no corroboration."""

    C2_TENTATIVE = "C2"
    """Preliminary evidence — needs additional validation."""

    C3_PROBABLE = "C3"
    """Multiple corroborating sources — reasonable to act on."""

    C4_CONFIRMED = "C4"
    """Verified through testing or rigorous audit."""

    C5_AXIOMATIC = "C5"
    """Foundational truth — contradicting this triggers premium audit."""


class BeliefStatus(str, Enum):
    """Lifecycle state of a belief in the cognitive layer."""

    ACTIVE = "active"
    """Belief is accepted and operational."""

    QUARANTINED = "quarantined"
    """Auditor detected contradiction — frozen pending resolution."""

    DEPRECATED = "deprecated"
    """Superseded by a newer belief — kept for provenance lineage."""

    CONTESTED = "contested"
    """Multiple conflicting beliefs exist — awaiting arbitration."""


class VerdictAction(str, Enum):
    """Actions the CognitiveHandoff can take on a belief."""

    ACCEPT = "accept"
    """Belief passed audit — safe to integrate."""

    QUARANTINE = "quarantine"
    """Contradiction detected — freeze and escalate."""

    REVISE = "revise"
    """Architect recommends schema/content revision."""

    SKIP = "skip"
    """Infrastructure prescreen: not worth auditing (compact_and_forget)."""

    ESCALATE = "escalate"
    """Deep Think uncertain — escalate to Opus premium audit."""


# ─── Provenance ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProvenanceEntry:
    """Single evidence link in the provenance chain.

    Immutable record of who/what contributed to a belief's existence.
    """

    source_type: str
    """Origin type: 'fact', 'belief', 'external', 'model_inference'."""

    source_id: str
    """Reference to the originating entity (fact ID, belief ID, URL)."""

    model: Optional[str]
    """Which LLM produced/validated this entry. None if human-sourced."""

    timestamp: str
    """ISO 8601 timestamp of this provenance action."""

    action: str
    """What happened: 'created', 'supported', 'contested', 'revised'."""


@dataclass(frozen=True)
class ProvenanceChain:
    """Immutable lineage of a belief's evidence.

    Ordered tuple — newest entries last. The chain is append-only;
    revising a belief creates a new BeliefObject with extended chain.
    """

    entries: tuple[ProvenanceEntry, ...] = ()

    def extend(self, entry: ProvenanceEntry) -> ProvenanceChain:
        """Return a new chain with the entry appended (immutable)."""
        return ProvenanceChain(entries=self.entries + (entry,))

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)


# ─── BeliefObject ───────────────────────────────────────────────────────────


def _uuid7() -> str:
    """Generate a UUID v7 (time-sortable) as string."""
    # UUID v7 not in stdlib until 3.14 — use v4 with timestamp prefix
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    uid = uuid.uuid4().hex
    return f"{ts}-{uid[:16]}"


def _now_iso() -> str:
    """Current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BeliefObject:
    """Immutable cognitive unit — the atom of the Belief Layer.

    A BeliefObject represents a single epistemological claim within CORTEX.
    It is created by the BeliefConsolidator (compression), validated by
    the CognitiveHandoff (quad-model audit), and stored in the ledger
    with cryptographic hash chain integrity.

    Frozen dataclass: mutation creates a new object with updated fields.
    Use dataclasses.replace() for field updates.
    """

    content: str
    """The belief statement in natural language."""

    project: str
    """Project namespace this belief belongs to."""

    tenant_id: str = "default"
    """Multi-tenant isolation key."""

    id: str = field(default_factory=_uuid7)
    """Time-sortable unique identifier."""

    confidence: BeliefConfidence = BeliefConfidence.C2_TENTATIVE
    """Epistemic confidence level (C1→C5)."""

    status: BeliefStatus = BeliefStatus.ACTIVE
    """Lifecycle state in the cognitive layer."""

    provenance: ProvenanceChain = field(default_factory=ProvenanceChain)
    """Ordered evidence chain — newest entries last."""

    created_at: str = field(default_factory=_now_iso)
    """When this belief was first created."""

    revised_at: Optional[str] = None
    """When this belief was last revised. None if never revised."""

    revision_count: int = 0
    """Number of times this belief has been revised."""

    contradicts: tuple[str, ...] = ()
    """IDs of beliefs this one contradicts (immutable tuple)."""

    supported_by: tuple[str, ...] = ()
    """IDs of beliefs/facts that corroborate this belief."""

    arbitrated_by: Optional[str] = None
    """Model identifier that last judged this belief (e.g., 'opus', 'deep_think')."""

    def is_axiomatic(self) -> bool:
        """Check if this belief has C5 confidence — triggers premium audit on conflict."""
        return self.confidence == BeliefConfidence.C5_AXIOMATIC

    def is_quarantined(self) -> bool:
        """Check if this belief is frozen pending contradiction resolution."""
        return self.status == BeliefStatus.QUARANTINED

    def to_dict(self) -> dict:
        """Serialize to dict for SQLite/JSON storage."""
        return {
            "id": self.id,
            "content": self.content,
            "confidence": self.confidence.value,
            "status": self.status.value,
            "provenance": [
                {
                    "source_type": e.source_type,
                    "source_id": e.source_id,
                    "model": e.model,
                    "timestamp": e.timestamp,
                    "action": e.action,
                }
                for e in self.provenance
            ],
            "created_at": self.created_at,
            "revised_at": self.revised_at,
            "revision_count": self.revision_count,
            "contradicts": list(self.contradicts),
            "supported_by": list(self.supported_by),
            "arbitrated_by": self.arbitrated_by,
            "project": self.project,
            "tenant_id": self.tenant_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BeliefObject:
        """Deserialize from dict (SQLite/JSON)."""
        provenance_entries = tuple(
            ProvenanceEntry(
                source_type=e["source_type"],
                source_id=e["source_id"],
                model=e.get("model"),
                timestamp=e["timestamp"],
                action=e["action"],
            )
            for e in data.get("provenance", [])
        )
        return cls(
            id=data["id"],
            content=data["content"],
            confidence=BeliefConfidence(str(data["confidence"])),
            status=BeliefStatus(str(data["status"])),
            provenance=ProvenanceChain(entries=provenance_entries),
            created_at=data["created_at"],
            revised_at=data.get("revised_at"),
            revision_count=data.get("revision_count", 0),
            contradicts=tuple(data.get("contradicts", [])),
            supported_by=tuple(data.get("supported_by", [])),
            arbitrated_by=data.get("arbitrated_by"),
            project=data["project"],
            tenant_id=data.get("tenant_id", "default"),
        )


# ─── BeliefVerdict ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BeliefVerdict:
    """Result of the CognitiveHandoff processing a belief.

    Returned by CognitiveHandoff.process_belief() — tells the caller
    what happened and which model made the decision.
    """

    action: VerdictAction
    """What the handoff decided to do."""

    model: str = "unknown"
    """Which model made this verdict (e.g., 'deep_think', 'opus', 'infra')."""

    contradictions: tuple[str, ...] = ()
    """IDs of contradicting beliefs (if action == QUARANTINE)."""

    revised_belief: Optional[BeliefObject] = None
    """Revised belief (if action == REVISE)."""

    cost_tokens: int = 0
    """Total tokens consumed across all model calls for this verdict."""

    reason: str = ""
    """Human-readable explanation of the verdict."""
