"""CORTEX v7 — Anamnesis-Ω: Circadian Cycle Models.

This module defines the foundational data structures for the Vigilia/Sueño 
(Wake/Sleep) memory cycle, introducing Shannon Entropy TTLs and 
Reputation-Weighted Asynchronous Byzantine Fault Tolerance (RWA-BFT).
"""

import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class TemporalCache(BaseModel):
    """Short-term memory (Vigilia) - High volatility, dynamic TTL.
    
    Data resides here while the system is 'awake'. Entropy and access
    patterns dictate survival until the next 'sleep' cycle for potential
    consolidation.
    """
    state_id: str = Field(description="Unique identifier for the volatile state")
    embedding: List[float] = Field(description="Vector representation")
    shannon_entropy: float = Field(description="Information density measuring surprise/novelty")
    dynamic_ttl: float = Field(description="Seconds until pruning if unaccessed")
    access_frequency: int = Field(default=1, description="Number of times accessed in current cycle")
    timestamp: float = Field(default_factory=time.time, description="Creation time")

class ConsolidatedMemoryGraph(BaseModel):
    """Long-term memory (Sueño) - Validated distributed storage.
    
    Data that survives Vigilia AND passes RWA-BFT consensus is crystallized
    here. Resistant to hallucinations and Byzantine attacks.
    """
    node_id: str = Field(description="Persistent identifier")
    core_semantic_data: dict = Field(description="The actual knowledge payload")
    synaptic_connections: List[str] = Field(default_factory=list, description="IDs of related nodes")
    dopamine_weight: float = Field(default=1.0, description="Connection strength based on TD-error")
    reputation_proof: float = Field(description="Aggregated reputation score of agents that validated this node")

class AgentNode(BaseModel):
    """Network participant identity for RWA-BFT consensus.
    
    Reputation is non-forgeable and updated via Markov Chains based on 
    historical consensus alignment.
    """
    agent_id: str = Field(description="Unique agent/model identifier")
    reputation: float = Field(default=1.0, ge=0.0, description="Current trust weight in the swarm")
