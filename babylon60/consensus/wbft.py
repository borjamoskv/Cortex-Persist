# [C5-REAL] Exergy-Maximized
"""
cat_id: consensus-wbft
cat_type: module
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
"""

from typing import NamedTuple


class SwarmVote(NamedTuple):
    agent_id: str
    provider: str
    model_family: str  # e.g., 'llama', 'qwen', 'openai'
    reputation: float
    vote_payload: str


class WeightedByzantineConsensus:
    """Implements Diversity-weighted BFT (INV-C01) to protect against
    Distillation Bias Sybil Attacks (swarm collusion due to shared model ancestry).
    """

    @staticmethod
    def compute_quorum(votes: list[SwarmVote]) -> tuple[str, float]:
        """Calculates consensus weighting each vote by diversity constraints."""
        if not votes:
            return "", 0.0

        scores: dict[str, float] = {}
        family_counts: dict[str, int] = {}

        # Count model family groupings to compute architectural penalty
        for vote in votes:
            family_counts[vote.model_family] = family_counts.get(vote.model_family, 0) + 1

        for vote in votes:
            # Multiplier: Reputation * Diversity
            # If 3 agents share the same 'llama' ancestry, their single weight is diluted
            diversity_divisor = family_counts[vote.model_family]
            weighted_vote = (vote.reputation * 1.0) / diversity_divisor

            scores[vote.vote_payload] = scores.get(vote.vote_payload, 0.0) + weighted_vote

        best_payload = max(scores, key=lambda p: scores[p])
        total_weight = sum(scores.values())
        consensus_ratio = scores[best_payload] / max(total_weight, 0.001)

        return best_payload, consensus_ratio
