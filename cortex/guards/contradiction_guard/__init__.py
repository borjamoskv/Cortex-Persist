"""
CORTEX - Contradiction Guard (Axiom 20: Epistemic Consistency).
"""

from __future__ import annotations

from .detector import detect_contradictions, scan_all_contradictions
from .models import ConflictCandidate, ConflictReport
from .scoring import EMBEDDING_BOOST_WEIGHT, _embedding_cosine_similarity

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "EMBEDDING_BOOST_WEIGHT",
    "_embedding_cosine_similarity",
    "detect_contradictions",
    "scan_all_contradictions",
]
