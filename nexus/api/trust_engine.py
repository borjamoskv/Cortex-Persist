"""NEXUS Trust Engine — Bayesian posterior trust scoring.

Standalone implementation derived from cortex.extensions.trust.bayesian.
Each agent's trust is modeled as a Beta(α, β) distribution.
Signals update the posterior, and the posterior mean maps to a TrustTier.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .models import TrustSignal, TrustTier


# ── Signal Weights ──────────────────────────────────────────────
# Each signal contributes (Δα, Δβ) to the posterior
_SIGNAL_WEIGHTS: dict[str, tuple[float, float]] = {
    TrustSignal.VERIFY.value: (3.0, 0.0),
    TrustSignal.TASK_COMPLETE.value: (2.0, 0.0),
    TrustSignal.TASK_FAIL.value: (0.0, 2.5),
    TrustSignal.REPORT.value: (0.0, 3.0),
    TrustSignal.VOUCH.value: (1.5, 0.0),
    TrustSignal.REVOKE.value: (0.0, 4.0),
}

# ── Tier Thresholds ─────────────────────────────────────────────
_TIER_THRESHOLDS: list[tuple[float, TrustTier]] = [
    (0.85, TrustTier.SOVEREIGN),
    (0.70, TrustTier.GOLD),
    (0.50, TrustTier.SILVER),
    (0.30, TrustTier.BRONZE),
    (0.00, TrustTier.UNVERIFIED),
]


@dataclass
class TrustState:
    """Mutable trust state for an agent."""

    alpha: float = 2.0  # Prior: mild trust
    beta: float = 2.0  # Prior: symmetric uncertainty
    total_signals: int = 0
    history: list[dict] = field(default_factory=list)

    @property
    def posterior_mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def posterior_variance(self) -> float:
        s = self.alpha + self.beta
        return (self.alpha * self.beta) / (s * s * (s + 1))

    @property
    def tier(self) -> TrustTier:
        mean = self.posterior_mean
        for threshold, tier in _TIER_THRESHOLDS:
            if mean >= threshold:
                return tier
        return TrustTier.UNVERIFIED

    @property
    def confidence_interval_95(self) -> tuple[float, float]:
        """Approximate 95% CI using normal approximation."""
        std = math.sqrt(self.posterior_variance)
        mean = self.posterior_mean
        return (max(0.0, mean - 1.96 * std), min(1.0, mean + 1.96 * std))

    def to_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "posterior_mean": round(self.posterior_mean, 4),
            "alpha": round(self.alpha, 2),
            "beta": round(self.beta, 2),
            "total_signals": self.total_signals,
            "history": self.history[-20:],  # Last 20 events
        }


class NexusTrustEngine:
    """Manages trust states for all registered agents."""

    def __init__(self):
        self._states: dict[str, TrustState] = {}

    def get_or_create(self, agent_id: str) -> TrustState:
        if agent_id not in self._states:
            self._states[agent_id] = TrustState()
        return self._states[agent_id]

    def apply_signal(
        self,
        agent_id: str,
        signal: TrustSignal,
        source: str = "system",
        reason: str = "",
        timestamp: str = "",
    ) -> TrustState:
        """Apply a trust signal to an agent's posterior."""
        state = self.get_or_create(agent_id)
        d_alpha, d_beta = _SIGNAL_WEIGHTS.get(signal.value, (0.0, 0.0))

        old_tier = state.tier
        state.alpha += d_alpha
        state.beta += d_beta
        state.total_signals += 1

        state.history.append(
            {
                "signal": signal.value,
                "source": source,
                "reason": reason,
                "timestamp": timestamp,
                "alpha_after": round(state.alpha, 2),
                "beta_after": round(state.beta, 2),
                "mean_after": round(state.posterior_mean, 4),
                "tier_after": state.tier.value,
                "tier_changed": state.tier != old_tier,
            }
        )

        return state

    def set_state(
        self,
        agent_id: str,
        alpha: float,
        beta: float,
        total_signals: int = 0,
        history: list | None = None,
    ):
        """Directly set trust state (for seeding)."""
        self._states[agent_id] = TrustState(
            alpha=alpha,
            beta=beta,
            total_signals=total_signals,
            history=history or [],
        )

    def get_all_states(self) -> dict[str, TrustState]:
        return self._states.copy()

    def rank_by_trust(self) -> list[tuple[str, float]]:
        """Return agents sorted by posterior mean descending."""
        return sorted(
            [(aid, s.posterior_mean) for aid, s in self._states.items()],
            key=lambda x: x[1],
            reverse=True,
        )
