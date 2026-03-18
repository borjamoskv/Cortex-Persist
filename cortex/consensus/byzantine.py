"""
CORTEX v6 — Unified Byzantine Consensus.

Consolidates WBFT (Weighted Byzantine Fault Tolerance) and HashConsensus
into a single, high-performance trust substrate.
Integrated with persistent ReputationManager.
"""

from __future__ import annotations

import collections
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from cortex.consensus.reputation import ReputationManager

logger = logging.getLogger("cortex.consensus.byzantine")


@dataclass
class ConsensusVerdict:
    """The outcome of a Byzantine agreement process."""

    consensus_reached: bool
    quorum_met: bool
    winning_data: Any
    confidence_score: float
    outliers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    """A single model's contribution to the consensus."""

    label: str
    content: str
    metadata: dict[str, Any] | None = None


class WBFTConsensus:
    """Weighted Byzantine Fault Tolerance for semantic data (LLM outputs)."""

    def __init__(self, threshold: float = 0.66) -> None:
        self.threshold = threshold

    async def evaluate(
        self, responses: list[ModelResponse], reputations: dict[str, float]
    ) -> ConsensusVerdict:
        """Evaluate semantic agreement using reputation-weighted clustering.

        Args:
            responses: List of ModelResponse objects.
            reputations: Dict mapping model labels to reputation scores [0.0, 1.0].
        """
        n = len(responses)
        if n == 0:
            return ConsensusVerdict(False, False, None, 0.0)

        # 1. Similarity Matrix Calculation (O(n^2))
        # For semantic data, we'd ideally use embeddings, but here we use a proxy (BLEU/Exact)
        matrix = {}
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    sim = 1.0
                else:
                    # Semantic Proxy: shared words ratio
                    set_i = set(responses[i].content.lower().split())
                    set_j = set(responses[j].content.lower().split())
                    if not set_i or not set_j:
                        sim = 0.0
                    else:
                        sim = len(set_i & set_j) / len(set_i | set_j)
                matrix[(i, j)] = matrix[(j, i)] = sim

        # 2. Weighted Agreement Score
        best_idx = -1
        max_score = -1.0
        scores = []

        for i in range(n):
            rep_i = reputations.get(responses[i].label, 0.5)
            w_sum = 0.0
            w_total = 0.0
            for j in range(n):
                if i == j:
                    continue
                rep_j = reputations.get(responses[j].label, 0.5)
                w_sum += matrix[(i, j)] * rep_j
                w_total += rep_j

            # Weighted mean similarity to all other nodes
            score = (w_sum / w_total) if w_total > 0 else 0.0
            scores.append(score)
            if score > max_score:
                max_score = score
                best_idx = i

        # 3. Verdict
        quorum_met = max_score >= self.threshold
        outliers = [responses[i].label for i, s in enumerate(scores) if s < (max_score * 0.5)]

        return ConsensusVerdict(
            consensus_reached=quorum_met,
            quorum_met=quorum_met,
            winning_data=responses[best_idx].content if best_idx >= 0 else None,
            confidence_score=max_score,
            outliers=outliers,
            metadata={"scores": {r.label: s for r, s in zip(responses, scores, strict=False)}},
        )


class HashConsensus:
    """Reputation-weighted consensus for deterministic or high-precision data."""

    def __init__(self, tolerance: float = 0.6) -> None:
        self.tolerance = tolerance

    def _hash(self, data: Any) -> str:
        if isinstance(data, (dict, list)):
            s = json.dumps(data, sort_keys=True)
        else:
            s = str(data)
        return hashlib.sha256(s.encode()).hexdigest()

    async def evaluate(
        self, proposals: dict[str, Any], reputations: dict[str, float]
    ) -> ConsensusVerdict:
        """Reach consensus via weighted voting on content hashes."""
        if not proposals:
            return ConsensusVerdict(False, False, None, 0.0)

        hashes = {label: self._hash(val) for label, val in proposals.items()}
        weights = collections.defaultdict(float)
        total_weight = 0.0

        for label, h in hashes.items():
            w = reputations.get(label, 0.5)
            weights[h] += w
            total_weight += w

        best_hash = None
        max_w = -1.0
        for h, w in weights.items():
            if w > max_w:
                max_w = w
                best_hash = h

        ratio = (max_w / total_weight) if total_weight > 0 else 0.0
        quorum_met = ratio >= self.tolerance

        winning_label = [l for l, h in hashes.items() if h == best_hash][0]
        outliers = [l for l, h in hashes.items() if h != best_hash]

        return ConsensusVerdict(
            consensus_reached=quorum_met,
            quorum_met=quorum_met,
            winning_data=proposals[winning_label] if quorum_met else None,
            confidence_score=ratio,
            outliers=outliers,
        )


class ByzantineArbiter:
    """The unified entry point for all consensus operations in CORTEX."""

    def __init__(self, db_conn: Any, threshold_semantic: float = 0.66, threshold_hash: float = 0.6):
        self._db = db_conn
        self.rep_manager = ReputationManager(db_conn)
        self.semantic = WBFTConsensus(threshold_semantic)
        self.hasher = HashConsensus(threshold_hash)

    async def evaluate_responses(self, responses: list[ModelResponse]) -> ConsensusVerdict:
        """Semantic evaluation with reputation updates."""
        # 1. Fetch reputations
        reps = {}
        for r in responses:
            reps[r.label] = await self.rep_manager.get_score(r.label)

        # 2. Evaluate
        verdict = await self.semantic.evaluate(responses, reps)

        # 3. Slashing/Reward (Asynchronous and Persistent)
        if verdict.consensus_reached:
            # Reward winner & contributors
            winners = [r.label for r in responses if r.label not in verdict.outliers]
            for label in winners:
                await self.rep_manager.reward(label, amount=0.01)

            # Slash outliers
            for label in verdict.outliers:
                await self.rep_manager.slash(label, penalty=0.05, reason="Consensus outlier")

        return verdict

    async def evaluate_data(self, proposals: dict[str, Any]) -> ConsensusVerdict:
        """Data evaluation (deterministic) with reputation updates."""
        reps = {}
        for label in proposals:
            reps[label] = await self.rep_manager.get_score(label)

        verdict = await self.hasher.evaluate(proposals, reps)

        if verdict.consensus_reached:
            # Reward
            winners = [l for l in proposals if l not in verdict.outliers]
            for label in winners:
                await self.rep_manager.reward(label, amount=0.01)

            # Slash
            for label in verdict.outliers:
                await self.rep_manager.slash(label, penalty=0.05, reason="BFT discrepancy")

        return verdict
