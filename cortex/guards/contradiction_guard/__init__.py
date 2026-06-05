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
"""

from __future__ import annotations

from cortex.guards.contradiction_guard.models import ConflictCandidate, ConflictReport
from cortex.guards.contradiction_guard.detector import (
    detect_contradictions,
    MAX_CANDIDATES,
    MIN_OVERLAP_SCORE,
)
from cortex.guards.contradiction_guard.scanner import scan_all_contradictions

# Internal imports required by tests or other modules
from cortex.guards.contradiction_guard.core import (
    _embedding_cosine_similarity,
    EMBEDDING_BOOST_WEIGHT,
    _fetch_decision_rows,
    _score_candidate,
)

from cortex.guards.contradiction_guard.utils import (
    _NOISE_PREFIXES,
    _STOP_WORDS,
    _NEGATION_MARKERS,
    _SUPERSESSION_MARKERS,
    _VERSION_PATTERN,
    _tokenize,
    _jaccard,
    _detect_negation,
    _detect_supersession,
    _extract_versions,
    _is_noise,
    _decrypt_content,
    _classify_conflict,
)

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "detect_contradictions",
    "scan_all_contradictions",
    "MAX_CANDIDATES",
    "MIN_OVERLAP_SCORE",
    # Internal variables/functions exposed for testing or backwards compatibility
    "_embedding_cosine_similarity",
    "EMBEDDING_BOOST_WEIGHT",
    "_fetch_decision_rows",
    "_score_candidate",
    "_NOISE_PREFIXES",
    "_STOP_WORDS",
    "_NEGATION_MARKERS",
    "_SUPERSESSION_MARKERS",
    "_VERSION_PATTERN",
    "_tokenize",
    "_jaccard",
    "_detect_negation",
    "_detect_supersession",
    "_extract_versions",
    "_is_noise",
    "_decrypt_content",
    "_classify_conflict",
]
