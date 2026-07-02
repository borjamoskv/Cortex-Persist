# [C5-REAL] Exergy-Maximized
"""
Belief Objects Schemas for CORTEX causal engine.
Strictly implements the RFC-CORTEX-NATIVE-AI specification.
"""

import enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BeliefState(str, enum.Enum):
    """Lifecycle state of a belief in the cognitive layer."""
    ACTIVE = "ACTIVE"
    CONTESTED = "CONTESTED"
    SUBSUMED = "SUBSUMED"
    DISCARDED = "DISCARDED"
    ORPHANED = "ORPHANED"


class ProvenanceEnvelope(BaseModel):
    """Immutable record of who/what contributed to a belief's existence."""
    source_hash: str
    source_type: Literal["agent", "tool", "human"]
    tenant_id: str
    signer_id: str
    signature: str = Field(..., description="CORTEX-TAINT signature")
    created_at: str = Field(..., description="UUIDv7 embedded chronos")
    was_generated_by: str = Field(..., description="PROV-AGENT episode ID")


class BeliefRelations(BaseModel):
    """Semantic CRDT mapping for pre-conditions and refutations."""
    entails: list[str] = Field(default_factory=list, description="Pre-conditions (BO IDs)")
    discards: list[str] = Field(default_factory=list, description="Refuted claims (BO IDs)")


class BeliefObject(BaseModel):
    """Immutable cognitive unit - the atom of the Belief Layer."""
    belief_id: str = Field(..., description="UUIDv7")
    proposition: str
    semantic_embedding: list[float] = Field(..., description="L2 vector projection")
    state: BeliefState
    confidence_score: float = Field(..., description="P(H|E) scalar value")
    variance: float = Field(..., description="Ignorance quantification")
    decay_rate: float = Field(..., description="Logarithmic epistemic fading")
    provenance: ProvenanceEnvelope
    relations: BeliefRelations


class VerdictAction(str, enum.Enum):
    """Actions the CognitiveHandoff can take on a belief."""
    ACCEPT = "accept"
    QUARANTINE = "quarantine"
    REVISE = "revise"
    SKIP = "skip"
    ESCALATE = "escalate"


class BeliefVerdict(BaseModel):
    """Result of the CognitiveHandoff processing a belief."""
    action: VerdictAction
    model: str = "unknown"
    contradictions: tuple[str, ...] = Field(default_factory=tuple)
    revised_belief: Optional[BeliefObject] = None
    cost_tokens: int = 0
    reason: str = ""
