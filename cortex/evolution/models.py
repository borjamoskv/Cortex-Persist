# cortex/evolution/models.py
"""Sovereign Evolution Models (350/100 standard).

Implements the structural types for agent evolution:
1. EvolutionType: The functional mode of an agent (Generalist to Singularity).
2. EvolutionMetric: Quantitative telemetry for the mutation ledger.
3. EvolutionMutation: A record of a discrete state change.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class EvolutionType(Enum):
    """Sovereign Agent Evolution tiers."""

    GENESIS = auto()  # Newly spawned, no history
    COGNITIVE = auto()  # Pattern-matching capable
    ADAPTIVE = auto()  # Feedback-loop integrated
    RECURSIVE = auto()  # Self-modifying logic
    SINGULARITY = auto()  # Optimal state-space convergence


@dataclass(frozen=True)
class EvolutionMetric:
    """Quantitative snapshot for the mutation ledger."""

    name: str
    value: float
    unit: str = "bits"
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class EvolutionMutation:
    """A record of a discrete state change in an agent."""

    agent_id: str
    mutation_type: str
    prev_hash: str
    new_hash: str
    delta_fitness: float
    metrics: list[EvolutionMetric] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "mutation_type": self.mutation_type,
            "prev_hash": self.prev_hash,
            "new_hash": self.new_hash,
            "delta_fitness": self.delta_fitness,
            "metrics": [{"name": m.name, "value": m.value, "unit": m.unit} for m in self.metrics],
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class CycleReport:
    """Metrics produced at the end of a single evolutionary cycle."""

    cycle: int
    avg_agent_fitness: float
    best_agent_fitness: float
    worst_agent_fitness: float
    avg_subagent_fitness: float
    total_mutations: int
    tournaments_run: int
    species_count: int
    duration_ms: float
    crossovers: int = 0
    extinctions: int = 0
    grace_injection: float = 0.0
    lagrangian_index: float = 0.0


@dataclass
class EngineParameters:
    """Hyperparameters for the Evolution Engine (Meta-Fitness targets)."""

    selection_pressure: float = 0.3
    mutation_rate: float = 0.1
    extinction_cycle: int = 10
    extinction_cull_rate: float = 0.5
    speciation_rate: float = 0.1
    lateral_transfer_rate: float = 0.15  # 350/100: Lateral Transfer
    meta_fitness_score: float = 0.0
