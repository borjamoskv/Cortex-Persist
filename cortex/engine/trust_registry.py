"""
Bayesian Trust Registry (Axiom Ω₃) — CORTEX Persist.

Converts "Bayesian Trust" from a decorative metric to an actionable consensus primitive.
Defines who has the mathematical right to mutate the persistent state.
"""

from __future__ import annotations

import dataclasses
import datetime
import logging
from collections.abc import Sequence
from typing import Optional

logger = logging.getLogger("cortex.engine.trust")


@dataclasses.dataclass()
class AgentTrustProfile:
    """Historical and dynamic trust profile for an executing agent."""

    agent_id: str
    prior: float = 0.5  # Base trust level before evidence
    successes: int = 0
    failures: int = 0
    taint_events: int = 0
    taint_severity_sum: float = 0.0
    last_incident_ts: Optional[datetime.datetime] = None
    last_success_ts: Optional[datetime.datetime] = None

    @property
    def total_events(self) -> int:
        return self.successes + self.failures


@dataclasses.dataclass()
class WeightedProposal:
    """A single deterministic proposal awaiting Thalamus collapse."""

    agent_id: str
    proposal_id: str
    action: str
    domain: str
    raw_confidence: float
    trust_score: float = 0.0
    influence_weight: float = 0.0
    final_score: float = 0.0
    reasoning_ref: Optional[str] = None


class TrustRegistry:
    """
    Epistemic arbiter for all CORTEX operations.
    Computes mathematical trust, penalizes taint, and handles probabilistic degradation.
    """

    def __init__(self, gamma: float = 2.0) -> None:
        """
        :param gamma: Influence attenuation exponent. Higher gamma severely
                      punishes low trust and amplifies high trust.
        """
        self.gamma = gamma
        # In memory storage for profiles, typically this would be backed by DB
        self._profiles: dict[str, AgentTrustProfile] = {}

    def get_profile(self, agent_id: str) -> AgentTrustProfile:
        if agent_id not in self._profiles:
            self._profiles[agent_id] = AgentTrustProfile(agent_id=agent_id)
        return self._profiles[agent_id]

    def register_feedback(
        self,
        agent_id: str,
        success: bool,
        is_taint: bool = False,
        taint_severity: float = 0.0,
        now: Optional[datetime.datetime] = None,
    ) -> None:
        """Record operational evidence for an agent."""
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)

        profile = self.get_profile(agent_id)
        if success:
            profile.successes += 1
            profile.last_success_ts = now
        else:
            profile.failures += 1
            if is_taint:
                profile.taint_events += 1
                profile.taint_severity_sum += taint_severity
                profile.last_incident_ts = now

    def compute_trust_score(
        self,
        profile: AgentTrustProfile,
        domain_risk_modifier: float = 1.0,
        now: Optional[datetime.datetime] = None,
    ) -> float:
        """
        trust(agent, domain) = base_prior + reliability_posterior - taint_penalty - drift_penalty
        Returns a normalized score in [0.0, 1.0].
        """
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)

        # 1. Base Reliability (Laplace smoothing)
        # Using a simple beta distribution mean approximation: (alpha + successes) / (alpha + beta + total)
        alpha, beta = 2.0 * profile.prior, 2.0 * (1.0 - profile.prior)
        reliability = (alpha + profile.successes) / (alpha + beta + profile.total_events)

        # 2. Taint Penalty
        # Taint heavily penalizes the raw score.
        taint_penalty = (profile.taint_events * 0.1) + (profile.taint_severity_sum * 0.15)

        # 3. Drift / Recency Penalty
        # If the last incident was recent, the penalty is higher.
        drift_penalty = 0.0
        if profile.last_incident_ts:
            delta_seconds = (now - profile.last_incident_ts).total_seconds()
            hours_since = delta_seconds / 3600.0
            # Decay the penalty over time (e.g., halflife of ~48 hours)
            if hours_since < 168:  # Only care about last 7 days
                drift_penalty = 0.2 * (1.0 - (hours_since / 168.0))

        # 4. Success Recovery Bonus
        # If there are successes *after* the last incident, soften the blow slightly
        recovery_bonus = 0.0
        if profile.last_success_ts and profile.last_incident_ts:
            if profile.last_success_ts > profile.last_incident_ts:
                recovery_bonus = 0.05  # Slight mechanical recovery, not instant amnesia

        raw_score = (
            profile.prior
            + (reliability - profile.prior)
            - taint_penalty
            - drift_penalty
            + recovery_bonus
        )

        # 5. Apply Domain Risk
        # Higher risk domains compress the score down closer to 0 if it's already low, or require higher absolute certainty
        # To keep it simple, we penalize the score if the domain risk is > 1.0
        if domain_risk_modifier > 1.0:
            penalty_factor = (domain_risk_modifier - 1.0) * 0.2
            raw_score -= penalty_factor

        # Normalize to [0, 1]
        return max(0.0, min(1.0, raw_score))

    def compute_influence_weight(self, trust_score: float) -> float:
        """
        inf_weight = trust_score ^ gamma
        gamma > 1 heavily penalizes mediocre agents and zeroes out tainted ones.
        """
        return trust_score**self.gamma

    def rank_proposals(
        self,
        proposals: Sequence[WeightedProposal],
        domain_risk_modifier: float = 1.0,
        now: Optional[datetime.datetime] = None,
    ) -> list[WeightedProposal]:
        """
        Hydrate proposals with trust math and rank them.
        """
        ranked = []
        for prop in proposals:
            profile = self.get_profile(prop.agent_id)
            score = self.compute_trust_score(profile, domain_risk_modifier, now)
            weight = self.compute_influence_weight(score)

            # The final score is a combination of the agent's influence weight and their raw confidence for this specific proposal
            final_score = weight * prop.raw_confidence

            # Mutate the dataclass (or create a new one)
            prop.trust_score = score
            prop.influence_weight = weight
            prop.final_score = final_score
            ranked.append(prop)

        ranked.sort(key=lambda p: p.final_score, reverse=True)
        return ranked

    def collapse_conflict(
        self,
        proposals: Sequence[WeightedProposal],
        domain_risk_modifier: float = 1.0,
        now: Optional[datetime.datetime] = None,
    ) -> tuple[Optional[WeightedProposal], dict[str, str]]:
        """
        Takes N proposals and returns the Single Winning Proposal (or None) + Diagnostic Reason Code.
        """
        if not proposals:
            return None, {"reason_code": "NO_PROPOSALS"}

        ranked = self.rank_proposals(proposals, domain_risk_modifier, now)

        if len(ranked) == 1:
            return ranked[0], {"reason_code": "SINGLE_CANDIDATE"}

        top = ranked[0]
        runner_up = ranked[1]

        # Tie break handling (AXIOM: determinism)
        if abs(top.final_score - runner_up.final_score) < 0.001:
            # Deterministic fallback: Highest prior wins
            top_prior = self.get_profile(top.agent_id).prior
            runner_prior = self.get_profile(runner_up.agent_id).prior
            if runner_prior > top_prior:
                return runner_up, {"reason_code": "TIE_BROKEN_BY_PRIOR"}
            elif runner_prior == top_prior:
                # Last resort: Hash comparison of proposal contents for absolute determinism
                top_hash = hash(top.action + top.agent_id)
                runner_hash = hash(runner_up.action + runner_up.agent_id)
                if runner_hash > top_hash:
                    return runner_up, {"reason_code": "TIE_BROKEN_BY_HASH"}
            return top, {"reason_code": "TIE_BROKEN_BY_PRIOR_OR_HASH"}

        return top, {"reason_code": "HIGHEST_INFLUENCE_WEIGHT"}
