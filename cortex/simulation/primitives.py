import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from cortex.interfaces.memory_provider import MemoryNode

@dataclass
class MemoryParticle:
    """
    A memory is an unstable particle, not a fixed object.
    """
    node_id: str
    state_vector: np.ndarray
    probability_mass: float
    temporal_phase: float
    entropy: float
    
    @classmethod
    def from_node(cls, node: MemoryNode, initial_mass: float = 1.0) -> 'MemoryParticle':
        # Default entropy starts low for raw nodes
        return cls(
            node_id=node.id,
            state_vector=np.array(node.embedding) if node.embedding is not None else np.zeros(384),
            probability_mass=initial_mass,
            temporal_phase=float(node.timestamp),
            entropy=0.1
        )

@dataclass
class MemoryTrajectory:
    """
    A sequence of particles through the graph representing a possible reality path.
    """
    particles: List[MemoryParticle] = field(default_factory=list)
    coherence_score: float = 0.0
    intent_alignment: float = 0.0
    novelty_bonus: float = 0.0
    entropy_penalty: float = 0.0
    
    @property
    def total_score(self) -> float:
        return self.coherence_score + self.intent_alignment - self.entropy_penalty + self.novelty_bonus

@dataclass
class SimulationField:
    """
    The resultant output: a superposition of trajectories or a collapsed narrative.
    """
    trajectories: List[MemoryTrajectory]
    is_collapsed: bool
    mode: str  # 'EXTRACTIVE_MODE', 'SUPERPOSITION_MODE', 'BIFURCATION_MODE'
    dominant_trajectory: Optional[MemoryTrajectory] = None
