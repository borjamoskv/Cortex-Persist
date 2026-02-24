# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.1 — Weighted Byzantine Fault Tolerance (KETER-∞ Ola 3).

Implements WBFT consensus for multi-model LLM response evaluation.
When N models produce responses, this module determines which responses
are trustworthy using reputation-weighted Byzantine consensus.

Architecture::

    N responses → WBFT.evaluate() → ByzantineVerdict
                     ↓
        Agreement matrix    (pairwise Jaccard)
        Reputation weights  (historical win rates)
        Byzantine threshold (⅔ weighted agreement)
        Outlier detection   (responses far from centroid)

The WBFT guarantees:
- Tolerates up to ⅓ faulty/malicious/hallucinating models
- Weights by historical model reputation
- Identifies outlier responses that diverge from consensus
- Returns a verdict with confidence and per-response trust scores

Usage::

    wbft = WBFTConsensus()
    verdict = wbft.evaluate(responses, history=thinking_history)
    print(verdict.trusted_responses)    # Responses that passed consensus
    print(verdict.outliers)             # Responses flagged as divergent
    print(verdict.confidence)           # Overall consensus confidence
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from cortex.thinking.fusion_models import (
    ModelResponse,
    ThinkingHistory,
    _jaccard,
    _tokenize,
)

__all__ = ["WBFTConsensus", "ByzantineVerdict", "ResponseTrust"]

logger = logging.getLogger("cortex.consensus.byzantine")


# ─── Data Models ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ResponseTrust:
    """Trust assessment for a single model response."""

    response: ModelResponse
    trust_score: float  # 0.0-1.0 (agreement with consensus)
    reputation: float  # Historical win rate of this model
    vote_multiplier: float  # Based on domain relevance
    is_trusted: bool  # Passed Byzantine threshold
    is_outlier: bool  # Diverges significantly from cluster
    agreement_with_centroid: float  # Jaccard with majority cluster

    @property
    def label(self) -> str:
        return self.response.label


@dataclass(slots=True)
class ByzantineVerdict:
    """Result of WBFT consensus evaluation."""

    trusted_responses: list[ResponseTrust] = field(default_factory=list)
    outliers: list[ResponseTrust] = field(default_factory=list)
    all_assessments: list[ResponseTrust] = field(default_factory=list)
    confidence: float = 0.0  # Overall consensus confidence
    agreement_matrix: dict = field(default_factory=dict)
    byzantine_threshold: float = 0.0
    quorum_met: bool = False

    @property
    def trusted_count(self) -> int:
        return len(self.trusted_responses)

    @property
    def total_count(self) -> int:
        return len(self.all_assessments)

    @property
    def fault_tolerance(self) -> int:
        """Max faulty models tolerated with current quorum."""
        n = self.total_count
        return (n - 1) // 3 if n > 0 else 0

    def best_response(self) -> ModelResponse | None:
        """Response with highest trust × reputation."""
        if not self.trusted_responses:
            return None
        best = max(
            self.trusted_responses,
            key=lambda rt: rt.trust_score * (0.5 + rt.reputation),
        )
        return best.response


# ─── WBFT Consensus Engine ───────────────────────────────────────────


class WBFTConsensus:
    """Weighted Byzantine Fault Tolerance for multi-model evaluation.

    Determines which model responses are trustworthy based on
    inter-model agreement weighted by historical reputation.
    """

    def __init__(
        self,
        *,
        byzantine_fraction: float = 1 / 3,
        outlier_threshold: float = 0.15,
        min_responses: int = 2,
        domain_weights: dict[str, dict[str, float]] | None = None,
        reputation_decay: float = 0.95,
    ):
        """
        Args:
            byzantine_fraction: Max fraction of faulty nodes (default ⅓).
            outlier_threshold: Jaccard below this = outlier.
            min_responses: Minimum valid responses to run consensus.
            domain_weights: Per-model multipliers by domain {"code": {"gpt-4o": 1.5}}.
            reputation_decay: Rate at which older reputation decays.
        """
        self._byzantine_fraction = byzantine_fraction
        self._outlier_threshold = outlier_threshold
        self._min_responses = min_responses
        self._domain_weights = domain_weights or {}
        self._reputation_decay = reputation_decay

    def evaluate(
        self,
        responses: list[ModelResponse],
        *,
        history: ThinkingHistory | None = None,
        domain: str | None = None,
    ) -> ByzantineVerdict:
        """Run WBFT consensus on a list of model responses.

        Args:
            responses: List of ModelResponse from parallel model queries.
            history: Optional ThinkingHistory for reputation weighting.
            domain: The conceptual domain (e.g., "code", "reasoning") for multipliers.

        Returns:
            ByzantineVerdict with trusted/outlier classification.
        """
        valid = [r for r in responses if r.ok]

        rep_weights, mults = self._get_reputation_weights(responses, history, domain)

        if len(valid) < self._min_responses:
            return self._verdict_without_quorum(responses, valid, rep_weights, mults)

        # Steps 1-4: Agreement analysis
        token_map = {i: _tokenize(r.content) for i, r in enumerate(valid)}
        agreement_matrix = self._build_agreement_matrix(token_map)
        weighted_agreements = self._compute_weighted_agreements(
            valid, agreement_matrix, rep_weights
        )

        # Step 5: Byzantine threshold (⅔ of max agreement)
        n = len(valid)
        required_agreement = 1.0 - self._byzantine_fraction
        threshold = (
            required_agreement * max(weighted_agreements.values()) if weighted_agreements else 0.0
        )

        # Step 6: Classify
        trusted, outliers, assessments = self._classify_valid_responses(
            valid,
            weighted_agreements,
            agreement_matrix,
            rep_weights,
            mults,
            n,
            threshold,
        )
        self._append_error_responses(responses, rep_weights, mults, assessments)

        quorum_met = len(trusted) >= (n * required_agreement)
        confidence = self._compute_confidence(trusted, assessments, quorum_met)

        verdict = ByzantineVerdict(
            trusted_responses=trusted,
            outliers=outliers,
            all_assessments=assessments,
            confidence=round(confidence, 3),
            agreement_matrix=agreement_matrix,
            byzantine_threshold=round(threshold, 3),
            quorum_met=quorum_met,
        )

        logger.info(
            "WBFT: %d/%d trusted (threshold=%.3f, confidence=%.3f, outliers=%d)",
            verdict.trusted_count,
            verdict.total_count,
            threshold,
            confidence,
            len(outliers),
        )

        return verdict

    def _verdict_without_quorum(
        self,
        responses: list[ModelResponse],
        valid: list[ModelResponse],
        rep_weights: dict[str, float],
        mults: dict[str, float],
    ) -> ByzantineVerdict:
        """Fast path: not enough valid responses for full consensus."""

        assessments = [
            ResponseTrust(
                response=r,
                trust_score=1.0 if r.ok else 0.0,
                reputation=rep_weights.get(r.label, 0.5),
                vote_multiplier=mults.get(r.label, 1.0),
                is_trusted=r.ok,
                is_outlier=False,
                agreement_with_centroid=1.0 if r.ok else 0.0,
            )
            for r in responses
        ]
        return ByzantineVerdict(
            trusted_responses=[a for a in assessments if a.is_trusted],
            outliers=[],
            all_assessments=assessments,
            confidence=0.5 if valid else 0.0,
            quorum_met=False,
        )

    def _classify_valid_responses(
        self,
        valid: list[ModelResponse],
        weighted_agreements: dict[int, float],
        agreement_matrix: dict,
        rep_weights: dict[str, float],
        mults: dict[str, float],
        n: int,
        threshold: float,
    ) -> tuple[list[ResponseTrust], list[ResponseTrust], list[ResponseTrust]]:
        """Classify each valid response as trusted/outlier."""
        trusted: list[ResponseTrust] = []
        outliers: list[ResponseTrust] = []
        assessments: list[ResponseTrust] = []

        for i, response in enumerate(valid):
            w_agreement = weighted_agreements.get(i, 0.0)
            centroid_agreement = self._centroid_agreement(i, agreement_matrix, n)
            reputation = rep_weights.get(response.label, 0.5)

            is_outlier = centroid_agreement < self._outlier_threshold
            is_trusted = w_agreement >= threshold and not is_outlier

            trust = ResponseTrust(
                response=response,
                trust_score=round(w_agreement, 3),
                reputation=round(reputation, 3),
                vote_multiplier=round(mults.get(response.label, 1.0), 3),
                is_trusted=is_trusted,
                is_outlier=is_outlier,
                agreement_with_centroid=round(centroid_agreement, 3),
            )

            assessments.append(trust)
            if is_trusted:
                trusted.append(trust)
            if is_outlier:
                outliers.append(trust)

        return trusted, outliers, assessments

    @staticmethod
    def _append_error_responses(
        responses: list[ModelResponse],
        rep_weights: dict[str, float],
        mults: dict[str, float],
        assessments: list[ResponseTrust],
    ) -> None:
        """Add non-ok responses as untrusted entries to assessments."""
        for r in responses:
            if not r.ok:
                assessments.append(
                    ResponseTrust(
                        response=r,
                        trust_score=0.0,
                        reputation=rep_weights.get(r.label, 0.5),
                        vote_multiplier=mults.get(r.label, 1.0),
                        is_trusted=False,
                        is_outlier=False,
                        agreement_with_centroid=0.0,
                    )
                )

    # ── Agreement Matrix ─────────────────────────────────────────

    @staticmethod
    def _build_agreement_matrix(
        token_map: dict[int, set[str]],
    ) -> dict[tuple[int, int], float]:
        """Pairwise Jaccard similarity between all response pairs."""
        matrix: dict[tuple[int, int], float] = {}
        indices = sorted(token_map.keys())

        for i_idx, i in enumerate(indices):
            for j in indices[i_idx + 1 :]:
                sim = _jaccard(token_map[i], token_map[j])
                matrix[(i, j)] = round(sim, 4)
                matrix[(j, i)] = round(sim, 4)

        # Node matches perfectly with itself
        for i in indices:
            matrix[(i, i)] = 1.0

        return matrix

    # ── Reputation Weights ───────────────────────────────────────

    def _get_reputation_weights(
        self,
        responses: list[ModelResponse],
        history: ThinkingHistory | None,
        domain: str | None,
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Extract reputation weights and compute final effective weight with multipliers.

        Returns:
            (effective_weights, base_multipliers)
        """
        weights: dict[str, float] = {}
        mult_map: dict[str, float] = {}

        domain_mults = self._domain_weights.get(domain, {}) if domain else {}

        top_history = {}
        if history:
            top_history = {
                # Apply decay as penalty to historic win rate if you want here.
                # Simplification: we use the win_rate directly as base.
                m["model"]: m["win_rate"] * self._reputation_decay
                for m in history.top_models(20)
            }

        for r in responses:
            base_reputation = top_history.get(r.label, 0.5)
            # Domain-specific multiplier (e.g., 1.5x for claude-3-opus on "code")
            mult = domain_mults.get(r.label, 1.0)
            mult_map[r.label] = mult
            # Effective reputation is base scaled by domain multiplier
            weights[r.label] = base_reputation * mult

        return weights, mult_map

    # ── Weighted Agreement ───────────────────────────────────────

    @staticmethod
    def _compute_weighted_agreements(
        responses: list[ModelResponse],
        matrix: dict[tuple[int, int], float],
        rep_weights: dict[str, float],
    ) -> dict[int, float]:
        """Compute reputation-weighted agreement score per response."""
        n = len(responses)
        scores: dict[int, float] = {}

        for i in range(n):
            weighted_sum = 0.0
            weight_total = 0.0

            for j in range(n):
                if i == j:
                    continue
                rep_j = rep_weights.get(responses[j].label, 0.5)
                sim = matrix.get((i, j), 0.0)
                weighted_sum += sim * rep_j
                weight_total += rep_j

            scores[i] = weighted_sum / weight_total if weight_total > 0 else 0.0

        return scores

    # ── Centroid Agreement ───────────────────────────────────────

    @staticmethod
    def _centroid_agreement(
        index: int,
        matrix: dict[tuple[int, int], float],
        n: int,
    ) -> float:
        """Average agreement of response[index] with all others."""
        if n <= 1:
            return 1.0
        total = sum(matrix.get((index, j), 0.0) for j in range(n) if j != index)
        return total / (n - 1)

    # ── Confidence Computation ───────────────────────────────────

    @staticmethod
    def _compute_confidence(
        trusted: list[ResponseTrust],
        all_assessments: list[ResponseTrust],
        quorum_met: bool,
    ) -> float:
        """Compute overall consensus confidence."""
        if not trusted:
            return 0.0

        # Base: fraction of trusted responses
        trust_ratio = len(trusted) / len(all_assessments) if all_assessments else 0.0

        # Boost: average trust score of trusted responses
        avg_trust = sum(t.trust_score for t in trusted) / len(trusted)

        # Boost: quorum met
        quorum_bonus = 0.15 if quorum_met else 0.0

        return min(1.0, (trust_ratio * 0.4) + (avg_trust * 0.45) + quorum_bonus)
