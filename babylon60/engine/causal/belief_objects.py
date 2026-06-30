# [C5-REAL] Exergy-Maximized
"""
Belief Objects Schemas for CORTEX causal engine.
"""

import enum
from datetime import datetime
from pydantic import BaseModel, Field

class BeliefState(str, enum.Enum):
    PROPOSED = "PROPOSED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"

class RelationType(str, enum.Enum):
    ENTAILS = "ENTAILS"
    CONTRADICTS = "CONTRADICTS"
    SUPPORTS = "SUPPORTS"
    INDEPENDENT = "INDEPENDENT"

class ProvenanceEnvelope(BaseModel):
    agent_id: str
    session_id: str
    timestamp: datetime
    signature: str = Field(..., description="CORTEX-TAINT signature")

class PropositionPayload(BaseModel):
    content: str
    context_hash: str
    certainty: float = Field(..., ge=0.0, le=1.0)

class BeliefObject(BaseModel):
    id: str
    state: BeliefState
    relation: RelationType
    provenance: ProvenanceEnvelope
    payload: PropositionPayload
