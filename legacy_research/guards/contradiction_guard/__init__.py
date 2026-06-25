# [C5-REAL] Exergy-Maximized
"""
CORTEX - Contradiction Guard (Axiom 20: Retrieval Consistency).

Every new decision must explicitly invalidate its predecessors or confirm
compatibility. This guard runs at store-time and returns potential
conflicts so the agent can disambiguate before persisting.

Strategy (4-layer, O(N) bounded):
  1. FTS5 keyword overlap - fast, coarse.
  2. Project+topic co-occurrence - medium precision.
  3. Negation / supersession detection - high precision.
  4. Embedding cosine similarity - semantic precision (graceful degradation).

Returns a ConflictReport with scored candidates.
"""

from __future__ import annotations

from legacy_research.guards.contradiction_guard.batch import scan_all_contradictions
from legacy_research.guards.contradiction_guard.detector import (
    MAX_CANDIDATES,
    MIN_OVERLAP_SCORE,
    detect_contradictions,
)
from legacy_research.guards.contradiction_guard.models import ConflictCandidate, ConflictReport
from legacy_research.guards.contradiction_guard.scoring import (
    EMBEDDING_BOOST_WEIGHT,
    _embedding_cosine_similarity,
)

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
