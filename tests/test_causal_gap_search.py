"""CORTEX — Causal Gap Search Test Suite.

Tests the causal gap retrieval engine (Axiom Ω₁₃).
Key invariant: a semantically similar but causally useless document
loses to a less similar document with higher evidence match.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CORTEX_TESTING", "1")

from cortex.search.causal_gap import (
    CausalGap,
    SearchCandidate,
    compute_candidate_score,
    retrieve_for_causal_gap,
)


def _gap() -> CausalGap:
    return CausalGap(
        decision_id="D-001",
        hypothesis="SQLite vec is faster than FAISS for < 100k docs",
        missing_evidence="benchmark comparison on 50k doc corpus",
        current_confidence=0.4,
        expected_confidence_gain=0.3,
        blocking_reason="architecture decision pending",
    )


# ── compute_candidate_score ──────────────────────────────────────────


class TestComputeCandidateScore:
    def test_perfect_scores(self) -> None:
        c = SearchCandidate("d1", 1.0, 1.0, 1.0, 1.0)
        score = compute_candidate_score(c)
        assert score == 1.0
        assert c.final_score == 1.0

    def test_zero_scores(self) -> None:
        c = SearchCandidate("d1", 0.0, 0.0, 0.0, 0.0)
        score = compute_candidate_score(c)
        assert score == 0.0

    def test_weights_applied_correctly(self) -> None:
        c = SearchCandidate("d1", 1.0, 0.0, 0.0, 0.0)
        score = compute_candidate_score(c)
        assert score == 0.25  # W_SEMANTIC = 0.25

    def test_evidence_dominates_semantic(self) -> None:
        """High semantic + zero evidence loses to low semantic + high evidence."""
        sim_heavy = SearchCandidate(
            "sim",
            semantic_score=0.95,
            evidence_match_score=0.1,
            confidence_gain_score=0.1,
            novelty_score=0.1,
        )
        evi_heavy = SearchCandidate(
            "evi",
            semantic_score=0.3,
            evidence_match_score=0.9,
            confidence_gain_score=0.8,
            novelty_score=0.3,
        )
        compute_candidate_score(sim_heavy)
        compute_candidate_score(evi_heavy)
        assert evi_heavy.final_score > sim_heavy.final_score


# ── retrieve_for_causal_gap ──────────────────────────────────────────


class TestRetrieveForCausalGap:
    def test_empty_corpus_returns_empty(self) -> None:
        result = retrieve_for_causal_gap(_gap(), [])
        assert result == []

    def test_top_k_truncation(self) -> None:
        corpus = [
            {
                "doc_id": f"d{i}",
                "semantic_score": 0.5,
                "evidence_match_score": 0.5,
                "confidence_gain_score": 0.5,
                "novelty_score": 0.5,
            }
            for i in range(20)
        ]
        result = retrieve_for_causal_gap(_gap(), corpus, top_k=5)
        assert len(result) == 5

    def test_ranking_by_causal_utility(self) -> None:
        """Causally useful doc beats semantically similar but useless doc."""
        corpus = [
            {
                "doc_id": "linkedin_embed",
                "semantic_score": 0.95,
                "evidence_match_score": 0.05,
                "confidence_gain_score": 0.05,
                "novelty_score": 0.1,
            },
            {
                "doc_id": "real_evidence",
                "semantic_score": 0.40,
                "evidence_match_score": 0.90,
                "confidence_gain_score": 0.85,
                "novelty_score": 0.5,
            },
        ]
        result = retrieve_for_causal_gap(_gap(), corpus, top_k=2)
        assert result[0].doc_id == "real_evidence"
        assert result[1].doc_id == "linkedin_embed"

    def test_all_candidates_get_scores(self) -> None:
        corpus = [
            {
                "doc_id": "a",
                "semantic_score": 0.3,
                "evidence_match_score": 0.7,
                "confidence_gain_score": 0.5,
                "novelty_score": 0.2,
            },
        ]
        result = retrieve_for_causal_gap(_gap(), corpus, top_k=10)
        assert len(result) == 1
        assert result[0].final_score > 0.0

    def test_missing_fields_default_to_zero(self) -> None:
        corpus = [{"doc_id": "sparse"}]
        result = retrieve_for_causal_gap(_gap(), corpus)
        assert len(result) == 1
        assert result[0].final_score == 0.0
