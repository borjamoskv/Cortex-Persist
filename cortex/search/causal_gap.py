"""Causal Gap Retrieval — Axiom Ω₁₃ Search Upgrade.

Replaces "give me similar results" with "give me the missing evidence
that most reduces uncertainty for decision D."

A document that is semantically similar but causally useless LOSES
to a less similar document that reduces the causal gap.

Status: IMPLEMENTED (upgraded from DECORATIVE via Ω₁₃ enforcement).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

__all__ = [
    "CausalGap",
    "SearchCandidate",
    "compute_candidate_score",
    "retrieve_for_causal_gap",
]

logger = logging.getLogger("cortex.search.causal_gap")

# ── Scoring weights ──────────────────────────────────────────────────
# Sum to 1.0. evidence_match and confidence_gain dominate by design.

W_SEMANTIC = 0.25
W_EVIDENCE = 0.35
W_CONFIDENCE_GAIN = 0.30
W_NOVELTY = 0.10


@dataclass
class CausalGap:
    """A gap in the causal chain that needs evidence to close.

    Attributes:
        decision_id: ID of the decision this gap blocks.
        hypothesis: What we believe but cannot yet confirm.
        missing_evidence: Description of what evidence would close this gap.
        current_confidence: Current confidence level (0.0–1.0).
        expected_confidence_gain: How much closing this gap would raise confidence.
        blocking_reason: Why this gap matters.
    """

    decision_id: str
    hypothesis: str
    missing_evidence: str
    current_confidence: float
    expected_confidence_gain: float
    blocking_reason: str


@dataclass
class SearchCandidate:
    """A candidate document scored against a causal gap.

    Attributes:
        doc_id: Document identifier.
        semantic_score: Cosine similarity to query (0.0–1.0).
        evidence_match_score: How well this matches missing_evidence (0.0–1.0).
        confidence_gain_score: Expected confidence gain (0.0–1.0).
        novelty_score: How novel this information is (0.0–1.0).
        final_score: Weighted composite score.
    """

    doc_id: str
    semantic_score: float
    evidence_match_score: float
    confidence_gain_score: float
    novelty_score: float
    final_score: float = 0.0


def compute_candidate_score(candidate: SearchCandidate) -> float:
    """Compute weighted composite score for a candidate.

    Formula:
        final = 0.25*semantic + 0.35*evidence + 0.30*confidence_gain + 0.10*novelty

    Returns:
        Composite score (can be negative if inputs are negative — clamp externally).
    """
    score = (
        W_SEMANTIC * candidate.semantic_score
        + W_EVIDENCE * candidate.evidence_match_score
        + W_CONFIDENCE_GAIN * candidate.confidence_gain_score
        + W_NOVELTY * candidate.novelty_score
    )
    candidate.final_score = round(score, 6)
    return candidate.final_score


def retrieve_for_causal_gap(
    gap: CausalGap,
    corpus: list[dict],
    top_k: int = 10,
) -> list[SearchCandidate]:
    """Retrieve documents ranked by causal gap reduction, not mere similarity.

    Each corpus item must have:
        - doc_id: str
        - semantic_score: float (pre-computed cosine similarity)
        - evidence_match_score: float (how well it matches missing_evidence)
        - confidence_gain_score: float (expected confidence gain)
        - novelty_score: float (information novelty)

    Args:
        gap: The causal gap to close.
        corpus: Pre-scored candidate documents.
        top_k: Maximum results to return.

    Returns:
        Top-k candidates sorted by causal utility (descending).
    """
    if not corpus:
        return []

    candidates: list[SearchCandidate] = []
    for doc in corpus:
        candidate = SearchCandidate(
            doc_id=doc.get("doc_id", "unknown"),
            semantic_score=doc.get("semantic_score", 0.0),
            evidence_match_score=doc.get("evidence_match_score", 0.0),
            confidence_gain_score=doc.get("confidence_gain_score", 0.0),
            novelty_score=doc.get("novelty_score", 0.0),
        )
        compute_candidate_score(candidate)
        candidates.append(candidate)

    # Sort by final_score descending — causal utility wins over similarity
    candidates.sort(key=lambda c: c.final_score, reverse=True)

    result = candidates[:top_k]

    logger.debug(
        "Causal gap retrieval for decision=%s: %d candidates → top_k=%d, best_score=%.4f",
        gap.decision_id,
        len(candidates),
        top_k,
        result[0].final_score if result else 0.0,
    )

    return result
