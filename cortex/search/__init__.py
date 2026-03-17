# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Search Package.

Status: IMPLEMENTED (Ω₁₃ — causal gap wired into hybrid search).
"""

from cortex.search.causal_gap import (
    CausalGap,
    SearchCandidate,
    compute_candidate_score,
    retrieve_for_causal_gap,
)
from cortex.search.hybrid import hybrid_search, hybrid_search_sync
from cortex.search.models import SearchResult
from cortex.search.text import text_search, text_search_sync
from cortex.search.vector import semantic_search, semantic_search_sync

__all__ = [
    "CausalGap",
    "SearchCandidate",
    "SearchResult",
    "compute_candidate_score",
    "hybrid_search",
    "hybrid_search_sync",
    "retrieve_for_causal_gap",
    "semantic_search",
    "semantic_search_sync",
    "text_search",
    "text_search_sync",
]
