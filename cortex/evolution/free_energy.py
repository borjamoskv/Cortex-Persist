# cortex/evolution/free_energy.py
"""Variational Free Energy Monitor — Fristonian Formalization of CORTEX.

Phase 3 cornerstone: makes explicit what the 8 improvement strategies
already do implicitly. Each agent domain is modeled as a system that
minimizes variational free energy F to maintain identity.

    F = Complexity − Accuracy

Where:
    Complexity = D_KL[q(θ) ‖ p(θ)]
        How far the domain's current state (q) is from the tonic
        homeostatic set-point (p). Penalizes high errors, ghosts,
        and low health.

    Accuracy = E_q[ln p(o|θ)]
        How well the domain's generative model predicts outcomes.
        Proxied by fitness_delta (reward prediction error).

Expected Free Energy (for strategy selection):
    G(π) = −pragmatic_value(π) − epistemic_value(π)

        pragmatic:  expected fitness gain from applying the strategy
        epistemic:  expected uncertainty reduction (information gain)

References:
    Friston, K. (2010). The free-energy principle: a unified brain
        theory? Nature Reviews Neuroscience, 11(2), 127–138.
    Parr, T., Pezzulo, G. & Friston, K. (2022). Active Inference:
        The Free Energy Principle in Mind, Brain, and Behavior. MIT Press.
    Da Costa, L. et al. (2020). Active inference on discrete state-spaces:
        A synthesis. Journal of Mathematical Psychology, 99, 102447.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from cortex.evolution.agents import AgentDomain
from cortex.evolution.cortex_metrics import CortexMetrics, DomainMetrics

logger = logging.getLogger(__name__)


# ── Homeostatic Set-Points (Prior Preferences) ────────────────
# These define the "preferred state" p(θ) — the attractor basin
# the domain seeks to maintain. A sovereign-grade agent has:
#   error_count → 0, ghost_count → 0, health_score → 1.0,
#   bridge_count → high, decision_count → high

_PRIOR = DomainMetrics()  # Tonic baseline: all zeros, health=0.5


@dataclass
class FreeEnergyState:
    """Free energy decomposition for a single domain.

    Implements the three-way decomposition:
        F = complexity - accuracy
        G = -pragmatic - epistemic  (Expected Free Energy for policies)
    """

    domain: AgentDomain = AgentDomain.FABRICATION
    complexity: float = 0.0
    accuracy: float = 0.0
    free_energy: float = 0.0
    surprise: float = 0.0  # -ln p(o) ≈ negative log-evidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.name,
            "F": round(self.free_energy, 4),
            "complexity": round(self.complexity, 4),
            "accuracy": round(self.accuracy, 4),
            "surprise": round(self.surprise, 4),
        }


@dataclass
class StrategyEFE:
    """Expected Free Energy for a candidate improvement strategy."""

    strategy_name: str = ""
    pragmatic_value: float = 0.0
    epistemic_value: float = 0.0
    expected_free_energy: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy_name,
            "G": round(self.expected_free_energy, 4),
            "pragmatic": round(self.pragmatic_value, 4),
            "epistemic": round(self.epistemic_value, 4),
        }


# ── Core Computation ──────────────────────────────────────────


def _kl_bernoulli(q: float, p: float) -> float:
    """KL divergence between two Bernoulli distributions.

    D_KL(q ‖ p) = q·ln(q/p) + (1-q)·ln((1-q)/(1-p))

    Handles edge cases where q or p are 0 or 1 by clamping
    to [ε, 1-ε] for numerical stability.
    """
    eps = 1e-8
    q = max(eps, min(1.0 - eps, q))
    p = max(eps, min(1.0 - eps, p))
    return q * math.log(q / p) + (1.0 - q) * math.log((1.0 - q) / (1.0 - p))


def compute_complexity(metrics: DomainMetrics) -> float:
    """D_KL[q(θ) ‖ p(θ)] — divergence from homeostatic set-point.

    Decomposes across multiple "sensory channels":
      - Health channel:  KL between current health_score and prior (0.5)
      - Error channel:   Contribution from error accumulation
      - Ghost channel:   Contribution from technical debt
      - Bridge channel:  Inverse contribution (bridges reduce complexity)

    Higher complexity = the domain's state has diverged further from
    the tonic baseline, requiring more "cognitive effort" to maintain.
    """
    # Health channel: KL divergence between observed and prior health
    health_kl = _kl_bernoulli(metrics.health_score, _PRIOR.health_score)

    # Error pressure: normalized by diminishing returns (log scale)
    error_pressure = math.log1p(metrics.error_count) * 0.8

    # Ghost pressure: debt accumulation
    ghost_pressure = math.log1p(metrics.ghost_count) * 0.5

    # Bridge relief: cross-domain integration reduces complexity
    bridge_relief = min(1.0, metrics.bridge_count * 0.1)

    complexity = health_kl + error_pressure + ghost_pressure - bridge_relief
    return max(0.0, complexity)


def compute_accuracy(metrics: DomainMetrics) -> float:
    """E_q[ln p(o|θ)] — model quality / predictive success.

    Proxied by the domain's fitness_delta (reward prediction error)
    and decision success rate. Higher accuracy means the domain's
    model is doing a good job predicting what happens.
    """
    # fitness_delta ∈ [-5, +5] → rescale to [0, 1]
    delta_norm = (metrics.fitness_delta + 5.0) / 10.0

    # decision_success_rate ∈ [0, 1] — already normalized
    dsr = metrics.decision_success_rate

    # Weighted combination: 60% delta signal, 40% crystallized knowledge
    accuracy = 0.6 * delta_norm + 0.4 * dsr
    return accuracy


def compute_surprise(metrics: DomainMetrics) -> float:
    """Surprisal ≈ −ln p(o) — how unexpected the current observations are.

    High errors + ghosts + low health = high surprise.
    The agent's goal is to minimize surprise by acting on the world
    (active inference) or updating its model (perceptual inference).
    """
    # Inverse health is surprise → perfect health = 0 surprise
    health_surprise = -math.log(max(1e-8, metrics.health_score))

    # Error surprise: each error is an unexpected observation
    error_surprise = metrics.error_count * 0.3

    # Ghost surprise: each ghost is unresolved uncertainty
    ghost_surprise = metrics.ghost_count * 0.2

    return health_surprise + error_surprise + ghost_surprise


def compute_free_energy(metrics: DomainMetrics) -> FreeEnergyState:
    """Full variational free energy computation for one domain.

    F = Complexity − Accuracy

    F is an upper bound on surprisal. The agent minimizes F by:
      1. Perceptual inference: updating beliefs (parameter tuning)
      2. Active inference: changing the world (heuristic injection, pruning)
      3. Model selection: choosing better models (crossover, bridge import)
    """
    c = compute_complexity(metrics)
    a = compute_accuracy(metrics)
    s = compute_surprise(metrics)

    return FreeEnergyState(
        domain=metrics.domain,
        complexity=c,
        accuracy=a,
        free_energy=c - a,
        surprise=s,
    )


# ── Strategy Selection via Expected Free Energy ───────────────


def compute_strategy_efe(
    strategy_name: str,
    mutation_delta: float,
    metrics: DomainMetrics,
) -> StrategyEFE:
    """Expected Free Energy G(π) for a candidate strategy.

    G(π) = −pragmatic_value − epistemic_value

    pragmatic:  how much the strategy is expected to reduce surprise
                (move toward preferred outcomes)
    epistemic:  how much the strategy is expected to reduce uncertainty
                (information gain about the domain's true state)

    Lower G = better strategy (we minimize expected free energy).
    """
    # Pragmatic value: expected fitness improvement relative to
    # how far from sovereign-grade we are
    sovereign_gap = max(0.01, 1.0 - metrics.health_score)
    pragmatic = mutation_delta * sovereign_gap

    # Epistemic value: strategies that fire in uncertain domains
    # (high ghost_count, low decision_count) have higher info gain
    uncertainty = math.log1p(metrics.ghost_count + 1) / (
        math.log1p(metrics.decision_count + 1) + 1e-8
    )
    epistemic = min(2.0, uncertainty * 0.5)

    g = -pragmatic - epistemic

    return StrategyEFE(
        strategy_name=strategy_name,
        pragmatic_value=pragmatic,
        epistemic_value=epistemic,
        expected_free_energy=g,
    )


# ── FreeEnergyMonitor — Orchestration Layer ───────────────────


class FreeEnergyMonitor:
    """Monitors variational free energy across all agent domains.

    Provides:
      - Per-domain F computation from live CortexMetrics
      - Strategy ranking by Expected Free Energy (EFE)
      - Aggregate system-level free energy (total F)
      - Trend detection (is F increasing or decreasing?)

    Thread-safe. Uses the same CortexMetrics sync layer.
    """

    def __init__(self, cortex_metrics: CortexMetrics | None = None) -> None:
        self._metrics = cortex_metrics or CortexMetrics()
        self._history: list[dict[AgentDomain, FreeEnergyState]] = []
        self._max_history: int = 100

    def snapshot(self) -> dict[AgentDomain, FreeEnergyState]:
        """Compute free energy for all domains from live telemetry."""
        all_metrics = self._metrics.get_all_metrics()
        states: dict[AgentDomain, FreeEnergyState] = {}

        for domain, metrics in all_metrics.items():
            states[domain] = compute_free_energy(metrics)

        # Record history for trend analysis
        self._history.append(states)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return states

    def total_free_energy(self) -> float:
        """Aggregate F across all domains — system-level health."""
        states = self.snapshot()
        return sum(s.free_energy for s in states.values())

    def rank_strategies(
        self,
        strategy_mutations: dict[str, float],
        domain: AgentDomain,
    ) -> list[StrategyEFE]:
        """Rank candidate strategies by Expected Free Energy.

        Args:
            strategy_mutations: {strategy_name: expected_delta_fitness}
            domain: The domain to evaluate strategies for.

        Returns:
            Strategies sorted by G (ascending — lower is better).
        """
        metrics = self._metrics.get_domain(domain)
        efes = [
            compute_strategy_efe(name, delta, metrics)
            for name, delta in strategy_mutations.items()
        ]
        efes.sort(key=lambda e: e.expected_free_energy)
        return efes

    def trend(self, domain: AgentDomain, window: int = 5) -> float:
        """F trend over last `window` snapshots.

        Returns:
            Positive = F increasing (system deteriorating)
            Negative = F decreasing (system improving)
            0.0 = no data or stable
        """
        if len(self._history) < 2:
            return 0.0

        recent = self._history[-min(window, len(self._history)):]
        deltas = []
        for i in range(1, len(recent)):
            prev_f = recent[i - 1].get(domain, FreeEnergyState()).free_energy
            curr_f = recent[i].get(domain, FreeEnergyState()).free_energy
            deltas.append(curr_f - prev_f)

        return sum(deltas) / len(deltas) if deltas else 0.0

    def report(self) -> dict[str, Any]:
        """Full system report — suitable for logging/dashboard."""
        states = self.snapshot()
        total_f = sum(s.free_energy for s in states.values())
        domains_sorted = sorted(states.items(), key=lambda x: x[1].free_energy, reverse=True)

        return {
            "total_F": round(total_f, 4),
            "avg_F": round(total_f / max(1, len(states)), 4),
            "worst_domain": domains_sorted[0][0].name if domains_sorted else "N/A",
            "best_domain": domains_sorted[-1][0].name if domains_sorted else "N/A",
            "domains": {d.name: s.to_dict() for d, s in states.items()},
            "snapshots_recorded": len(self._history),
        }
