"""Causality data models — Taint status, confidence ordering, fact nodes.

Tri-state taint (CLEAN/SUSPECT/TAINTED) prevents binary overshoot:
a boolean taint would rupture half the DAG on a mild suspicion.
"""

from __future__ import annotations
from typing import Optional

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "Confidence",
    "CONFIDENCE_ORDER",
    "FactNode",
    "REVERSE_CONFIDENCE_ORDER",
    "TaintStatus",
]


class Confidence(str, Enum):
    """Epistemic confidence levels C1 (hypothesis) → C5 (confirmed)."""

    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


class TaintStatus(str, Enum):
    """Tri-state causal taint.

    - CLEAN: no contamination detected
    - SUSPECT: at least one parent is tainted, but threshold not reached
    - TAINTED: node is invalidated or ≥50% parents are tainted
    """

    CLEAN = "clean"
    SUSPECT = "suspect"
    TAINTED = "tainted"


# Ordinal mapping for confidence arithmetic
CONFIDENCE_ORDER: dict[Confidence, int] = {
    Confidence.C1: 1,
    Confidence.C2: 2,
    Confidence.C3: 3,
    Confidence.C4: 4,
    Confidence.C5: 5,
}

REVERSE_CONFIDENCE_ORDER: dict[int, Confidence] = {v: k for k, v in CONFIDENCE_ORDER.items()}


@dataclass
class FactNode:
    """A node in the causal DAG with taint and confidence tracking.

    Attributes:
        fact_id: Unique identifier for this fact.
        confidence: Original assessed confidence level.
        effective_confidence: Confidence after taint propagation adjustments.
        invalidated: Whether this fact has been explicitly invalidated.
        taint_status: Current taint state (clean/suspect/tainted).
        parents: IDs of parent nodes in the causal DAG.
        children: IDs of child nodes in the causal DAG.
        source: Origin of the fact (agent:gemini, human, cli, api).
    """

    fact_id: str
    confidence: Confidence
    effective_confidence: Confidence
    invalidated: bool = False
    taint_status: TaintStatus = TaintStatus.CLEAN
    parents: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    source: Optional[str] = None
