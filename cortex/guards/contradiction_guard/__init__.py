"""
CORTEX - Contradiction Guard (Axiom 20: Epistemic Consistency).

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

from cortex.guards.contradiction_guard.batch import scan_all_contradictions
from cortex.guards.contradiction_guard.detector import (
    EMBEDDING_BOOST_WEIGHT,
    MAX_CANDIDATES,
    MIN_OVERLAP_SCORE,
    _embedding_cosine_similarity,
    _fetch_decision_rows,
    _score_candidate,
    detect_contradictions,
)
from cortex.guards.contradiction_guard.models import ConflictCandidate, ConflictReport
from cortex.guards.contradiction_guard.utils import (
    _classify_conflict,
    _decrypt_content,
    _detect_negation,
    _detect_supersession,
    _extract_versions,
    _is_noise,
    _jaccard,
    _tokenize,
)

__all__ = [
    # Main API
    "detect_contradictions",
    "scan_all_contradictions",
    # Models
    "ConflictCandidate",
    "ConflictReport",
    # Internal variables & aliases used directly by tests
    "_embedding_cosine_similarity",
    "EMBEDDING_BOOST_WEIGHT",
    "MAX_CANDIDATES",
    "MIN_OVERLAP_SCORE",
    # Internal helpers used directly by tests
    "_tokenize",
    "_jaccard",
    "_detect_negation",
    "_detect_supersession",
    "_extract_versions",
    "_is_noise",
    "_decrypt_content",
    "_classify_conflict",
    "_score_candidate",
    "_fetch_decision_rows",
]
