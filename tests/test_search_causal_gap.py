"""Tests for causal gap retrieval — Ω₁₃ §15.9."""

from __future__ import annotations

from cortex.search.causal_gap import CausalGap, retrieve_for_causal_gap


def test_missing_evidence_closes_gap_faster() -> None:
    """Documents matching missing evidence score higher than purely semantic matches."""
    gap = CausalGap(
        decision_id="D-123",
        hypothesis="The system is metastable",
        missing_evidence="Logs showing silent failures",
        current_confidence=0.4,
        expected_confidence_gain=0.3,
        blocking_reason="Need to determine if refactor is safe",
    )

    corpus = [
        # Purely semantic match, but lacks evidence
        {
            "doc_id": "doc_semantic",
            "semantic_score": 0.9,
            "evidence_match_score": 0.1,
            "confidence_gain_score": 0.1,
            "novelty_score": 0.0,
        },
        # Lower semantic match, but exactly hits the missing evidence
        {
            "doc_id": "doc_evidence",
            "semantic_score": 0.4,
            "evidence_match_score": 0.9,
            "confidence_gain_score": 0.8,
            "novelty_score": 0.5,
        },
    ]

    results = retrieve_for_causal_gap(gap, corpus, top_k=2)

    assert len(results) == 2
    # The evidence doc should win over the pure semantic doc
    assert results[0].doc_id == "doc_evidence"
    assert results[0].final_score > results[1].final_score


def test_empty_corpus() -> None:
    """Empty input returns empty output."""
    gap = CausalGap("D-1", "H", "E", 0.5, 0.2, "R")
    assert retrieve_for_causal_gap(gap, []) == []


def test_top_k_sorting() -> None:
    """Returns top-k results sorted descending by score."""
    gap = CausalGap("D-1", "H", "E", 0.5, 0.2, "R")
    corpus = [
        {"doc_id": "low", "semantic_score": 0.1},
        {"doc_id": "high", "semantic_score": 0.9, "evidence_match_score": 0.9},
        {"doc_id": "med", "semantic_score": 0.5, "evidence_match_score": 0.5},
    ]

    results = retrieve_for_causal_gap(gap, corpus, top_k=2)
    assert len(results) == 2
    assert results[0].doc_id == "high"
    assert results[1].doc_id == "med"


def test_property_score_bounds() -> None:
    """Property: All 1.0 inputs yield exactly 1.0 final score."""
    gap = CausalGap("D-1", "H", "E", 0.5, 0.2, "R")
    corpus = [
        {
            "doc_id": "max",
            "semantic_score": 1.0,
            "evidence_match_score": 1.0,
            "confidence_gain_score": 1.0,
            "novelty_score": 1.0,
        }
    ]
    results = retrieve_for_causal_gap(gap, corpus)
    assert results[0].final_score == 1.0


def test_property_score_zero_bounds() -> None:
    """Property: Missing inputs default to 0.0, yielding exactly 0.0 final score."""
    gap = CausalGap("D-1", "H", "E", 0.5, 0.2, "R")
    corpus = [{"doc_id": "min"}]  # No scores provided
    results = retrieve_for_causal_gap(gap, corpus)
    assert results[0].final_score == 0.0


def test_property_score_negative_propagation() -> None:
    """Property: Negative inputs propagate without truncation (delegated to clamp)."""
    gap = CausalGap("D-1", "H", "E", 0.5, 0.2, "R")
    corpus = [
        {
            "doc_id": "neg",
            "semantic_score": -1.0,
            "evidence_match_score": -1.0,
            "confidence_gain_score": -1.0,
            "novelty_score": -1.0,
        }
    ]
    results = retrieve_for_causal_gap(gap, corpus)
    assert results[0].final_score == -1.0

