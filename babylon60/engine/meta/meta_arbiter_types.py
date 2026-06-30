from decimal import Decimal
# [C5-REAL] Exergy-Maximized
"""CORTEX Meta-Arbiter Types.

Data structures for Cognitive Arbitration.

Reality Level: C5-REAL
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class Resolution(Enum):
    """The arbiter's final disposition."""

    CONSENSUS = auto()  # All layers agree (within threshold)
    LEDGER_OVERRIDE = auto()  # Ledger truth overrides probabilistic layers
    WEIGHTED_FUSION = auto()  # Layers disagree; fused by weight
    ABSTAIN = auto()  # Insufficient confidence from all layers
    CONFLICT = auto()  # Irreconcilable divergence; requires human review


class LayerID(Enum):
    L1_EMBEDDING = "L1_EMBEDDING"
    L2_TOPOLOGY = "L2_TOPOLOGY"
    L3_LEDGER = "L3_LEDGER"
    L4_RL = "L4_RL"


@dataclass(frozen=True)
class LayerSignal:
    """A normalized signal from one cognitive layer."""

    layer: LayerID
    score: Decimal  # Normalized [0.0, 1.0] confidence/relevance
    raw_value: Any  # Original value from the layer (for audit)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(
                f"[META-ARBITER] LayerSignal score must be in [0,1], got {self.score} "
                f"from {self.layer.value}"
            )


@dataclass(frozen=True)
class ConflictPair:
    """Records a detected contradiction between two layers."""

    layer_a: LayerID
    layer_b: LayerID
    divergence: float  # |score_a - score_b|
    description: str


@dataclass(frozen=True)
class ArbiterVerdict:
    """The canonical output of the Meta-Arbiter."""

    resolution: Resolution
    fused_score: Decimal  # Final arbitrated confidence [0,1]
    winning_layer: LayerID | None  # Which layer dominated (if applicable)
    conflicts: list[ConflictPair]
    layer_signals: dict[str, float]  # Snapshot of all input scores
    audit_hash: str  # SHA-256 of the verdict for ledger tracing
    reasoning: str  # Human-readable justification
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

    @property
    def is_actionable(self) -> bool:
        """Whether this verdict provides a clear direction."""
        return self.resolution not in (Resolution.ABSTAIN, Resolution.CONFLICT)
