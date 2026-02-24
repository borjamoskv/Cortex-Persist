from dataclasses import dataclass
from enum import Enum
from typing import Any


class Dimension(Enum):
    ZERO_FRICTION = "A"
    TEMPORAL_SOVEREIGNTY = "B"
    AESTHETIC_SOVEREIGNTY = "C"
    ETHICAL_MANAGEMENT = "D"


@dataclass
class CuatridaMetrics:
    # Dimension A: Zero-Friction
    finitud_density: float = 1.0  # 0.0 to 1.0 (1.0 = Zero anticipation stress)
    latency_ms: float = 0.0

    # Dimension B: Temporal Sovereignty
    causal_certainty: float = 1.0  # Percentage of immutable chain integrity
    decision_count: int = 0

    # Dimension C: Aesthetic Sovereignty
    aesthetic_honor: float = 100.0  # MEJORAlo score baseline
    entropy_density: float = 0.0

    # Dimension D: Ethical Management
    computational_respect: float = 1.0  # Token efficiency ratio
    oracle_invocations: int = 0


@dataclass
class DecisionNode:
    tx_id: int
    project: str
    intent: str
    dimension: Dimension
    metrics: CuatridaMetrics
    timestamp: str
    causal_link: int | None = None  # Reference to previous tx_id
    metadata: dict[str, Any] | None = None
