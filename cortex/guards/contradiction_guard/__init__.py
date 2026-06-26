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

from .batch import (
    _build_token_index,
    _compare_decisions,
    _prepare_decisions,
    _process_token_bucket,
    scan_all_contradictions,
)
from .detector import (
    MAX_CANDIDATES,
    MIN_OVERLAP_SCORE,
    _fetch_decision_rows,
    detect_contradictions,
)
from .models import ConflictCandidate, ConflictReport
from .scoring import _classify_conflict, _score_candidate
from .utils import (
    _NEGATION_MARKERS,
    _NOISE_PREFIXES,
    _STOP_WORDS,
    _SUPERSESSION_MARKERS,
    _VERSION_PATTERN,
    EMBEDDING_BOOST_WEIGHT,
    _decrypt_content,
    _detect_negation,
    _detect_supersession,
    _embedding_cosine_similarity,
    _extract_versions,
    _is_noise,
    _jaccard,
    _tokenize,
)

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "EMBEDDING_BOOST_WEIGHT",
    "MAX_CANDIDATES",
    "MIN_OVERLAP_SCORE",
    "_NEGATION_MARKERS",
    "_NOISE_PREFIXES",
    "_STOP_WORDS",
    "_SUPERSESSION_MARKERS",
    "_VERSION_PATTERN",
    "_build_token_index",
    "_classify_conflict",
    "_compare_decisions",
    "_decrypt_content",
    "_detect_negation",
    "_detect_supersession",
    "_embedding_cosine_similarity",
    "_extract_versions",
    "_fetch_decision_rows",
    "_is_noise",
    "_jaccard",
    "_prepare_decisions",
    "_process_token_bucket",
    "_score_candidate",
    "_tokenize",
    "detect_contradictions",
    "scan_all_contradictions",
]
