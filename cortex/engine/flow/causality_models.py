# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EpistemicStatus(str, Enum):
    CONJECTURE = "conjecture"
    TEST_PASSED = "test_passed"
    REFUTED = "refuted"
    OBSOLETE = "obsolete"


class TaintStatus(str, Enum):
    """Tri-state causal taint (Ω₁₃)."""

    CLEAN = "clean"
    SUSPECT = "suspect"
    TAINTED = "tainted"


class Confidence(str, Enum):
    """Ordinal confidence levels C1 (lowest) -> C5 (highest)."""

    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


EDGE_DERIVED_FROM = "derived_from"
EDGE_TRIGGERED_BY = "triggered_by"
EDGE_UPDATED_FROM = "updated_from"
EDGE_TAINTED_BY = "tainted_by"

CONFIDENCE_ORDER: list[Confidence] = [
    Confidence.C1,
    Confidence.C2,
    Confidence.C3,
    Confidence.C4,
    Confidence.C5,
]
CONFIDENCE_LEVELS: list[str] = [c.value for c in reversed(CONFIDENCE_ORDER)]


def _downgrade_confidence(current: str, hops: int) -> str:
    """Downgrade confidence by *hops* levels (floor = C1)."""
    try:
        idx = CONFIDENCE_ORDER.index(Confidence(current))
    except ValueError:
        return Confidence.C1.value
    new_idx = max(0, idx - hops)
    return CONFIDENCE_ORDER[new_idx].value


@dataclass(frozen=True)
class TaintReport:
    """Immutable record of a taint propagation run."""

    source_fact_id: int
    affected_count: int
    confidence_changes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LedgerEvent:
    event_id: str
    parent_ids: list[str]
    status: EpistemicStatus
    trust_score: float
    created_at: str
    last_revalidated_at: str | None = None
    tainted: bool = False
