from decimal import Decimal
# [C5-REAL] Exergy-Maximized
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryParticle:
    content: str
    weight: float = 1.0
    probability_mass: float = 1.0
    temporal_phase: float = 1.0
    entropy: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryTrajectory:
    particles: list[MemoryParticle] = field(default_factory=list)
    confidence: float = 1.0
    total_score: Decimal = 0.0
    coherence_score: Decimal = 1.0
    entropy_penalty: float = 0.0


@dataclass
class SimulationField:
    trajectories: list[MemoryTrajectory] = field(default_factory=list)
    is_collapsed: bool = False
    mode: str = "DEFAULT"
    dominant_trajectory: MemoryTrajectory | None = None
