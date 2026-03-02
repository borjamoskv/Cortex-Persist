"""Bayesian Trust Updater — Sovereign confidence as a running posterior.

Treats fact confidence as a Beta distribution:
  - alpha (α): successes — confirmations, high-confidence citations
  - beta  (β): failures  — contradictions, low-confidence evidence

After enough updates the posterior mean converges naturally to C5/C4/C3.
We write the result back to `facts.confidence` and `facts.consensus_score`.

Usage:
    updater = BayesianTrustUpdater(engine)
    result = await updater.update(fact_id=42, signal=Signal.CONFIRM)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["BayesianTrustUpdater", "Signal", "TrustUpdate"]

logger = logging.getLogger("cortex.trust")


# Confidence → (α₀, β₀) priors — start from empirical base rates
_PRIORS: dict[str, tuple[float, float]] = {
    "C5": (9.0, 1.0),   # Very strong prior toward trust
    "C4": (7.0, 3.0),
    "C3": (5.0, 5.0),   # Symmetric — uncertain
    "C2": (3.0, 7.0),
    "C1": (1.0, 9.0),   # Very strong prior toward distrust
    "unknown": (2.0, 2.0),
}

# Posterior mean → confidence label thresholds
_THRESHOLDS: list[tuple[float, str]] = [
    (0.85, "C5"),
    (0.70, "C4"),
    (0.50, "C3"),
    (0.30, "C2"),
    (0.00, "C1"),
]

# Update weights per signal type
_SIGNAL_WEIGHTS: dict[str, tuple[float, float]] = {
    "confirm":      (2.0, 0.0),   # Strong evidence for
    "weak_confirm": (1.0, 0.0),   # Weak evidence for
    "contradict":   (0.0, 2.0),   # Strong evidence against
    "weak_contradict": (0.0, 1.0),# Weak evidence against
    "replicate":    (1.5, 0.0),   # Independent replication
    "deprecate":    (0.0, 3.0),   # Explicit invalidation
}


class Signal(str, Enum):
    """Evidence signal for a stored fact."""
    CONFIRM = "confirm"
    WEAK_CONFIRM = "weak_confirm"
    CONTRADICT = "contradict"
    WEAK_CONTRADICT = "weak_contradict"
    REPLICATE = "replicate"
    DEPRECATE = "deprecate"


@dataclass
class TrustUpdate:
    """Result of a Bayesian trust update."""
    fact_id: int
    signal: str
    old_confidence: str
    new_confidence: str
    old_consensus_score: float
    new_consensus_score: float
    alpha: float               # Posterior α
    beta: float                # Posterior β
    posterior_mean: float      # E[p] = α / (α + β)
    posterior_variance: float  # Var[p] = αβ / (α+β)²(α+β+1)
    confidence_changed: bool


def _posterior_mean(alpha: float, beta: float) -> float:
    return alpha / (alpha + beta)


def _posterior_variance(alpha: float, beta: float) -> float:
    s = alpha + beta
    return (alpha * beta) / (s * s * (s + 1))


def _map_to_confidence(mean: float) -> str:
    for threshold, label in _THRESHOLDS:
        if mean >= threshold:
            return label
    return "C1"


class BayesianTrustUpdater:
    """Updates fact confidence using a Beta-distributed posterior."""

    __slots__ = ("_engine",)

    def __init__(self, engine: CortexEngine) -> None:
        self._engine = engine

    async def update(
        self,
        fact_id: int,
        signal: Signal | str,
        tenant_id: str = "default",
    ) -> TrustUpdate:
        """Apply a Bayesian update to a fact's confidence.

        Args:
            fact_id: The fact to update.
            signal: Evidence signal (confirm, contradict, replicate…).
            tenant_id: Tenant scope.

        Returns:
            TrustUpdate with old/new confidence and posterior params.
        """
        sig = Signal(signal) if isinstance(signal, str) else signal
        conn = await self._engine.get_conn()

        # Fetch current state
        cursor = await conn.execute(
            "SELECT confidence, consensus_score FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Fact {fact_id} not found for tenant '{tenant_id}'")

        old_conf: str = row[0] or "C3"
        old_score: float = float(row[1]) if row[1] is not None else 1.0

        # Build posterior from prior + signal
        alpha0, beta0 = _PRIORS.get(old_conf, _PRIORS["C3"])
        d_alpha, d_beta = _SIGNAL_WEIGHTS[sig.value]
        alpha = alpha0 + d_alpha
        beta = beta0 + d_beta

        mean = _posterior_mean(alpha, beta)
        variance = _posterior_variance(alpha, beta)
        new_conf = _map_to_confidence(mean)
        # consensus_score = posterior mean (bounded 0–1)
        new_score = round(mean, 4)

        # Write back
        await conn.execute(
            "UPDATE facts SET confidence = ?, consensus_score = ? WHERE id = ? AND tenant_id = ?",
            (new_conf, new_score, fact_id, tenant_id),
        )
        await conn.commit()

        result = TrustUpdate(
            fact_id=fact_id,
            signal=sig.value,
            old_confidence=old_conf,
            new_confidence=new_conf,
            old_consensus_score=old_score,
            new_consensus_score=new_score,
            alpha=round(alpha, 4),
            beta=round(beta, 4),
            posterior_mean=round(mean, 4),
            posterior_variance=round(variance, 6),
            confidence_changed=(new_conf != old_conf),
        )

        logger.info(
            "BayesTrust: fact=%d signal=%s %s→%s (mean=%.3f α=%.1f β=%.1f)",
            fact_id, sig.value, old_conf, new_conf, mean, alpha, beta,
        )
        return result

    async def batch_update(
        self,
        fact_ids: list[int],
        signal: Signal | str,
        tenant_id: str = "default",
    ) -> list[TrustUpdate]:
        """Update multiple facts with the same signal."""
        results = []
        for fid in fact_ids:
            try:
                r = await self.update(fid, signal, tenant_id)
                results.append(r)
            except ValueError as e:
                logger.warning("BayesTrust batch skip: %s", e)
        return results

    async def inspect(
        self,
        fact_id: int,
        tenant_id: str = "default",
    ) -> dict:
        """Return current posterior state for a fact without modifying it."""
        conn = await self._engine.get_conn()
        cursor = await conn.execute(
            "SELECT confidence, consensus_score FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Fact {fact_id} not found")

        conf = row[0] or "C3"
        score = float(row[1]) if row[1] is not None else 1.0
        alpha0, beta0 = _PRIORS.get(conf, _PRIORS["C3"])

        return {
            "fact_id": fact_id,
            "confidence": conf,
            "consensus_score": score,
            "prior_alpha": alpha0,
            "prior_beta": beta0,
            "prior_mean": round(_posterior_mean(alpha0, beta0), 4),
            "required_to_upgrade": _upgrades_needed(conf),
        }


def _upgrades_needed(current: str) -> dict:
    """How many CONFIRM signals are needed to upgrade to the next level."""
    order = ["C1", "C2", "C3", "C4", "C5"]
    idx = order.index(current) if current in order else 2
    result = {}
    for target in order[idx + 1:]:
        a0, b0 = _PRIORS.get(current, _PRIORS["C3"])
        # Simulate confirms until posterior mean crosses next threshold
        threshold, _ = next(
            ((t, lbl) for t, lbl in _THRESHOLDS if lbl == target), (0.85, "C5")
        )
        a, b = a0, b0
        needed = 0
        while _posterior_mean(a, b) < threshold and needed < 100:
            a += _SIGNAL_WEIGHTS["confirm"][0]
            needed += 1
        result[target] = needed if needed < 100 else "≥100"
    return result
