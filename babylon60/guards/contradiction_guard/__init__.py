# [C5-REAL] Exergy-Maximized
"""
CORTEX - Contradiction Guard Package (Axiom 20: Epistemic Consistency).

Every new decision must explicitly invalidate its predecessors or confirm
compatibility. This guard runs at store-time and returns potential
conflicts so the agent can disambiguate before persisting.
"""

from babylon60.guards.contradiction_guard.detector import (
    EMBEDDING_BOOST_WEIGHT,
    MAX_CANDIDATES,
    MIN_OVERLAP_SCORE,
    _embedding_cosine_similarity,
    detect_contradictions,
)
from babylon60.guards.contradiction_guard.models import ConflictCandidate, ConflictReport
from babylon60.guards.contradiction_guard.scanner import scan_all_contradictions

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "EMBEDDING_BOOST_WEIGHT",
    "MAX_CANDIDATES",
    "MIN_OVERLAP_SCORE",
    "_embedding_cosine_similarity",
    "detect_contradictions",
    "scan_all_contradictions",
]
