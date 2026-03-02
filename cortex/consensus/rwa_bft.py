# cortex/consensus/rwa_bft.py
"""RWA-BFT — Reputation-Weighted Asynchronous Byzantine Fault Tolerance.

Implements the formal consensus protocol specified in CORTEX Phase 2 v3
for validating fact injections from evolutionary agents.

Mathematical Foundation
-----------------------
Supermajority condition (Eq. 1):
    Σᵢ∈Validators Rᵢ > (2/3) × Σₖ₌₁ᴺ Rₖ

Markov reputation update (Eq. 2):
    Rᵢ⁽ᵗ⁺¹⁾ = λ·Rᵢ⁽ᵗ⁾ + (1−λ)·Φ(vᵢ, V_final)

Where:
    λ  ∈ [0,1]  — historical memory factor (default: 0.85)
    Φ  — reward function:
          +1.0  if agent voted with consensus (correct)
          −3.0  if agent submitted a byzantine fault (tamper attempt)
           0.0  if agent abstained

Liveness Guarantee:
    If > (1/3) of weighted reputation is honest, consensus is reachable.

References:
    Castro & Liskov (1999). Practical Byzantine Fault Tolerance.
    Van Valen (1973). A New Evolutionary Law.
    Lamport, Shostak & Pease (1982). The Byzantine Generals Problem.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger("cortex.consensus.rwa_bft")

__all__ = [
    "AgentVote",
    "ConsensusResult",
    "RWABFTConsensus",
    "VoteOutcome",
]


# ── Vote type registry ─────────────────────────────────────────────────────


class VoteOutcome(Enum):
    """The result of a single agent's vote."""

    FOR = auto()         # Agent agrees the fact is valid
    AGAINST = auto()     # Agent rejects the fact as invalid
    ABSTAIN = auto()     # Agent has insufficient context to vote


# ── Data Models ────────────────────────────────────────────────────────────


@dataclass
class AgentVote:
    """A single vote cast by an evolutionary agent on a fact injection.

    Attributes:
        agent_id:    Unique identifier of the voting agent.
        fact_id:     Identifier of the fact being validated.
        outcome:     FOR / AGAINST / ABSTAIN.
        confidence:  Agent self-reported confidence ∈ [0, 1].
        timestamp:   Wall-clock time of the vote (UTC epoch).
        payload:     Optional signed payload for tamper detection.
    """

    agent_id: str
    fact_id: str
    outcome: VoteOutcome
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """Output of an RWA-BFT round.

    Attributes:
        fact_id:             The fact that was evaluated.
        accepted:            True if supermajority agreed the fact is valid.
        supermajority_met:   Whether the Σᵢ Rᵢ > 2/3 × Σ condition was met.
        total_reputation:    Σₖ Rₖ — total active reputation in this round.
        approving_reputation: Σᵢ∈FOR Rᵢ.
        byzantine_detected:  True if any agent submitted a fault-flagged vote.
        quorum_size:         Number of agents that participated (non-abstain).
        confidence:          Weighted average confidence of FOR votes.
        outlier_agents:      Agent IDs flagged as potential byzantine nodes.
        timestamp:           When the result was computed.
    """

    fact_id: str
    accepted: bool
    supermajority_met: bool
    total_reputation: float
    approving_reputation: float
    byzantine_detected: bool = False
    quorum_size: int = 0
    confidence: float = 0.0
    outlier_agents: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def approval_ratio(self) -> float:
        """Fraction of active reputation that approved the fact."""
        if self.total_reputation < 1e-9:
            return 0.0
        return self.approving_reputation / self.total_reputation

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "accepted": self.accepted,
            "supermajority_met": self.supermajority_met,
            "approval_ratio": round(self.approval_ratio, 4),
            "approving_reputation": round(self.approving_reputation, 4),
            "total_reputation": round(self.total_reputation, 4),
            "byzantine_detected": self.byzantine_detected,
            "quorum_size": self.quorum_size,
            "confidence": round(self.confidence, 4),
            "outlier_agents": self.outlier_agents,
        }


# ── RWA-BFT Engine ─────────────────────────────────────────────────────────


class RWABFTConsensus:
    """Reputation-Weighted Asynchronous Byzantine Fault Tolerance.

    Validates fact injections from evolutionary agents using weighted
    supermajority consensus with Markov reputation updates.

    Usage::

        consensus = RWABFTConsensus()

        votes = [
            AgentVote("agent_A", "fact_001", VoteOutcome.FOR),
            AgentVote("agent_B", "fact_001", VoteOutcome.FOR),
            AgentVote("agent_C", "fact_001", VoteOutcome.AGAINST),
        ]

        result = consensus.evaluate("fact_001", votes)
        if result.accepted:
            # Trust injection — supermajority validated
            ...

    Attributes:
        memory_factor (λ):   Weight given to historical reputation vs current vote.
        byzantine_threshold: Reputation fraction required for supermajority (2/3).
        min_quorum:          Minimum non-abstaining agents required.
        outlier_z_threshold: Z-score above which a low-reputation voter is flagged.
    """

    def __init__(
        self,
        *,
        memory_factor: float = 0.85,
        byzantine_threshold: float = 2.0 / 3.0,
        min_quorum: int = 2,
        outlier_z_threshold: float = 2.0,
        initial_reputation: float = 1.0,
    ) -> None:
        """
        Args:
            memory_factor (λ):       Historical weight in reputation update ∈ [0, 1].
            byzantine_threshold:     Supermajority fraction (default 2/3).
            min_quorum:              Min non-abstaining voters to run consensus.
            outlier_z_threshold:     Z-score cutoff to flag byzantine nodes.
            initial_reputation:      Default reputation for new agents.
        """
        self._lambda = memory_factor
        self._threshold = byzantine_threshold
        self._min_quorum = min_quorum
        self._outlier_z = outlier_z_threshold
        self._initial_rep = initial_reputation

        # Markov reputation ledger: agent_id → Rᵢ
        self._reputation: dict[str, float] = {}
        # Vote history for auditing: fact_id → ConsensusResult
        self._history: dict[str, ConsensusResult] = {}

    # ── Public API ────────────────────────────────────────────────────

    def reputation(self, agent_id: str) -> float:
        """Get current reputation of an agent (initialises to default if new)."""
        return self._reputation.get(agent_id, self._initial_rep)

    def evaluate(self, fact_id: str, votes: list[AgentVote]) -> ConsensusResult:
        """Run one RWA-BFT round over the provided votes.

        Supermajority condition (Eq. 1):
            Σᵢ∈FOR Rᵢ > (2/3) × Σₖ Rₖ

        After the round, updates all agent reputations via Markov chain (Eq. 2).

        Args:
            fact_id: Identifier of the fact being evaluated.
            votes:   List of AgentVote submitted by participating agents.

        Returns:
            ConsensusResult with acceptance decision and diagnostic metadata.
        """
        if not votes:
            logger.warning("RWA-BFT: No votes for fact %s — returning rejected.", fact_id)
            return ConsensusResult(
                fact_id=fact_id,
                accepted=False,
                supermajority_met=False,
                total_reputation=0.0,
                approving_reputation=0.0,
            )

        # ── Step 1: Partition votes ────────────────────────────────────
        for_votes = [v for v in votes if v.outcome == VoteOutcome.FOR]
        against_votes = [v for v in votes if v.outcome == VoteOutcome.AGAINST]
        non_abstain = for_votes + against_votes

        if len(non_abstain) < self._min_quorum:
            logger.info(
                "RWA-BFT: fact=%s quorum not met (%d < %d)",
                fact_id, len(non_abstain), self._min_quorum,
            )
            result = ConsensusResult(
                fact_id=fact_id,
                accepted=False,
                supermajority_met=False,
                total_reputation=self._total_rep(votes),
                approving_reputation=self._weighted_rep(for_votes),
                quorum_size=len(non_abstain),
            )
            self._history[fact_id] = result
            return result

        # ── Step 2: Compute reputation masses ─────────────────────────
        total_rep = self._total_rep(non_abstain)
        approving_rep = self._weighted_rep(for_votes)

        # Eq. 1 — Supermajority check
        supermajority_met = (total_rep > 0) and (
            approving_rep > self._threshold * total_rep
        )

        # ── Step 3: Detect Byzantine outliers ─────────────────────────
        outliers, byzantine_detected = self._detect_outliers(
            for_votes, against_votes, total_rep
        )

        # ── Step 4: Weighted confidence of FOR votes ───────────────────
        confidence = self._weighted_confidence(for_votes) if for_votes else 0.0

        result = ConsensusResult(
            fact_id=fact_id,
            accepted=supermajority_met and not byzantine_detected,
            supermajority_met=supermajority_met,
            total_reputation=total_rep,
            approving_reputation=approving_rep,
            byzantine_detected=byzantine_detected,
            quorum_size=len(non_abstain),
            confidence=confidence,
            outlier_agents=outliers,
        )

        # ── Step 5: Markov reputation update ──────────────────────────
        # V_final is FOR if supermajority accepted; AGAINST otherwise
        final_vote = VoteOutcome.FOR if supermajority_met else VoteOutcome.AGAINST
        self._update_reputations(votes, final_vote)

        self._history[fact_id] = result
        logger.info(
            "RWA-BFT: fact=%s accepted=%s (FOR=%.2f / TOTAL=%.2f, threshold=%.2f%%), "
            "outliers=%s",
            fact_id, result.accepted,
            approving_rep, total_rep, self._threshold * 100,
            outliers or "none",
        )
        return result

    def audit(self) -> list[dict[str, Any]]:
        """Return all historical consensus results as serialisable dicts."""
        return [r.to_dict() for r in self._history.values()]

    # ── Internal helpers ──────────────────────────────────────────────

    def _rep(self, agent_id: str) -> float:
        """Get reputation, clamped to [0.01, ∞) to prevent zero-weight collapse."""
        return max(0.01, self._reputation.get(agent_id, self._initial_rep))

    def _total_rep(self, votes: list[AgentVote]) -> float:
        """Σₖ Rₖ over the provided vote list."""
        return sum(self._rep(v.agent_id) for v in votes)

    def _weighted_rep(self, votes: list[AgentVote]) -> float:
        """Σᵢ Rᵢ for a subset of votes (weighted by agent reputation)."""
        return sum(self._rep(v.agent_id) for v in votes)

    def _weighted_confidence(self, for_votes: list[AgentVote]) -> float:
        """Reputation-weighted average confidence of FOR votes."""
        if not for_votes:
            return 0.0
        total_rep = self._weighted_rep(for_votes)
        if total_rep < 1e-9:
            return 0.0
        return sum(
            v.confidence * self._rep(v.agent_id) for v in for_votes
        ) / total_rep

    def _detect_outliers(
        self,
        for_votes: list[AgentVote],
        against_votes: list[AgentVote],
        total_rep: float,
    ) -> tuple[list[str], bool]:
        """Flag agents whose vote diverges significantly from the reputation mass.

        An agent in the minority (AGAINST while the FOR mass is dominant)
        is flagged as a potential byzantine node if its reputation Z-score
        is anomalously low relative to the group mean.

        Returns:
            (outlier_agent_ids, byzantine_detected)
        """
        outliers: list[str] = []
        byzantine = False

        if total_rep < 1e-9:
            return outliers, byzantine

        # Majority direction by reputation mass
        for_rep = self._weighted_rep(for_votes)
        against_rep = self._weighted_rep(against_votes)
        majority_is_for = for_rep >= against_rep

        minority_votes = against_votes if majority_is_for else for_votes
        if not minority_votes:
            return outliers, byzantine

        # Z-score of minority reputations vs all non-abstaining agents
        all_reps = [self._rep(v.agent_id) for v in for_votes + against_votes]
        if len(all_reps) < 2:
            return outliers, byzantine

        mean_rep = sum(all_reps) / len(all_reps)
        variance = sum((r - mean_rep) ** 2 for r in all_reps) / len(all_reps)
        std_rep = variance ** 0.5

        for v in minority_votes:
            r = self._rep(v.agent_id)
            z = (mean_rep - r) / std_rep if std_rep > 0.0 else 0.0
            if z > self._outlier_z:
                # Low-reputation minority voter — possible byzantine injection
                outliers.append(v.agent_id)
                byzantine = True
                logger.warning(
                    "RWA-BFT: Possible byzantine node detected: %s (rep=%.3f, z=%.2f)",
                    v.agent_id, r, z,
                )

        return outliers, byzantine

    def _phi(self, vote: AgentVote, final: VoteOutcome) -> float:
        """Reward function Φ(vᵢ, V_final).

        Returns:
            +1.0  Voted with consensus.
            −3.0  Byzantine fault (voted against consensus with high confidence).
             0.0  Abstained.
        """
        if vote.outcome == VoteOutcome.ABSTAIN:
            return 0.0
        if vote.outcome == final:
            return 1.0
        # Penalise dissent proportionally to confidence — high-confidence
        # opposition in a clear consensus is a stronger byzantine signal.
        return -3.0 * vote.confidence

    def _update_reputations(
        self, votes: list[AgentVote], final: VoteOutcome
    ) -> None:
        """Apply Markov reputation updates (Eq. 2) for all participating agents.

        Rᵢ⁽ᵗ⁺¹⁾ = λ·Rᵢ⁽ᵗ⁾ + (1−λ)·Φ(vᵢ, V_final)

        Reputations are clamped to [0.01, 10.0] to prevent:
          - Collapse to zero (zero-weight agents can't recover).
          - Unbounded growth (single agent dominates consensus).
        """
        for vote in votes:
            aid = vote.agent_id
            current = self._rep(aid)
            phi = self._phi(vote, final)
            updated = self._lambda * current + (1.0 - self._lambda) * phi
            self._reputation[aid] = max(0.01, min(10.0, updated))
            logger.debug(
                "RWA-BFT: reputation update %s: %.3f → %.3f (φ=%.2f)",
                aid, current, self._reputation[aid], phi,
            )
