"""MOSKV-1 — Tesseract Manifold Data Models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DimensionType(str, Enum):
    D1_PERCEPTION = "D1"
    D2_DECISION = "D2"
    D3_CREATION = "D3"
    D4_VALIDATION = "D4"


@dataclass
class DimensionalState:
    """State of a single dimension within the manifold."""

    dimension: DimensionType
    convergence: float = 0.0  # 0.0 to 1.0
    active: bool = True
    output: Any = None
    messages: list[str] = field(default_factory=list)


@dataclass
class ConvergenceMetrics:
    """Mathematical metrics evaluating the wave's convergence."""

    entropy_delta: float = 0.0  # Should be <= 0
    siege_survival_rate: float = 0.0  # Should be >= 0.95
    prediction_accuracy: float = 0.0  # Should be >= 0.70
    fitness_score: float = 0.0  # Should be >= 0.85
    intent_drift: float = 0.0  # Should be <= 0.10

    def has_converged(self) -> bool:
        """Returns True if the manifold has reached mathematical convergence."""
        return (
            self.entropy_delta <= 0.0
            and self.siege_survival_rate >= 0.95
            and self.prediction_accuracy >= 0.70
            and self.fitness_score >= 0.85
            and self.intent_drift <= 0.10
        )


@dataclass
class WaveState:
    """The standing wave state representing the whole manifold at a given cycle."""

    cycle: int = 0
    metrics: ConvergenceMetrics = field(default_factory=ConvergenceMetrics)
    dimensions: dict[DimensionType, DimensionalState] = field(
        default_factory=lambda: {
            DimensionType.D1_PERCEPTION: DimensionalState(DimensionType.D1_PERCEPTION),
            DimensionType.D2_DECISION: DimensionalState(DimensionType.D2_DECISION),
            DimensionType.D3_CREATION: DimensionalState(DimensionType.D3_CREATION),
            DimensionType.D4_VALIDATION: DimensionalState(DimensionType.D4_VALIDATION),
        }
    )
