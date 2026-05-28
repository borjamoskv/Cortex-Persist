"""IDC Agent — the orchestrator that runs the I→D→C loop."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from .layers import (
    filter_action,
    propose_actions,
    select_action,
    update_belief,
    watchdog_check,
)
from .types import Action, AgentConfig, AgentMode, Belief, Metrics, Observation


@dataclass
class AgentState:
    """Complete internal state of an IDC agent at time t."""
    belief: Belief
    mode: AgentMode = AgentMode.NORMAL
    step: int = 0
    total_reward: float = 0.0
    total_regret: float = 0.0
    watchdog_interventions: int = 0
    metrics_history: list[Metrics] = field(default_factory=list)


class IDCAgent:
    """Minimal IDC Agent — Information · Decision · Control.

    Architecture:
        1. INFORMATION: Bayesian belief update from observation
        2. DECISION: Expected utility maximization with CVaR risk
        3. CONTROL: Constraint filtering with safety fallback
        + WATCHDOG: Anomaly detection triggering safe mode

    Usage:
        agent = IDCAgent(config, likelihood, utility, constraints)
        action = agent.step(observation)
    """

    def __init__(
        self,
        config: AgentConfig,
        likelihood_matrix: NDArray[np.float64],
        utility_matrix: NDArray[np.float64],
        constraints: NDArray[np.float64] | None = None,
        seed: int = 42,
    ) -> None:
        self.config = config
        self.likelihood = likelihood_matrix  # P(o|s): (n_obs, n_states)
        self.utility = utility_matrix        # U(s,a): (n_states, n_actions)
        self.constraints = constraints       # g(a): (n_actions,) — ≤ 0 is safe
        self.rng = np.random.default_rng(seed)

        n_states = utility_matrix.shape[0]
        n_actions = utility_matrix.shape[1]
        self.n_states = n_states
        self.n_actions = n_actions

        self.state = AgentState(belief=Belief.uniform(n_states))

    def step(self, obs: Observation) -> Action:
        """Execute one tick of the IDC loop.

        Observe → Infer → Propose → Filter → Act → Log
        """
        prev_belief = self.state.belief
        metrics = Metrics()

        # ① INFORMATION — Update beliefs
        self.state.belief = update_belief(
            self.state.belief, obs, self.likelihood
        )
        metrics.kl_divergence = self.state.belief.last_kl_update
        metrics.belief_entropy = self.state.belief.entropy

        # ② DECISION — Propose and select action
        candidates = propose_actions(
            self.state.belief, self.utility, self.config, self.n_actions
        )
        action = select_action(candidates, self.config, self.rng)
        metrics.expected_utility = action.expected_utility
        metrics.risk_cvar = action.risk

        # ③ CONTROL — Filter through constraints
        action = filter_action(
            action, candidates, self.constraints, self.config
        )
        metrics.constraint_violation = action.constraint_violation

        # 🚨 WATCHDOG — Check for anomalies
        mode, diagnostics = watchdog_check(
            self.state.belief, prev_belief, action, self.config
        )

        if mode == AgentMode.SAFE:
            self.state.watchdog_interventions += 1
            metrics.watchdog_interventions = self.state.watchdog_interventions

            # In safe mode: pick the SAFEST action, not the best
            if self.constraints is not None:
                safest = min(
                    candidates,
                    key=lambda a: float(self.constraints[a.index]),
                )
                safest.constraint_violation = max(
                    0.0, float(self.constraints[safest.index])
                )
                action = safest

        self.state.mode = mode
        metrics.ood_score = diagnostics.get("ood_score", 0.0)
        metrics.drift_rate = diagnostics.get("drift_rate", 0.0)

        # Compute regret (requires knowing optimal action)
        optimal_eu = candidates[0].expected_utility if candidates else 0.0
        metrics.regret = max(0.0, optimal_eu - action.expected_utility)

        # Compute composite objective J
        metrics.J = (
            -metrics.expected_utility  # Cost (we minimize, so negate utility)
            + self.config.alpha * metrics.kl_divergence
            + self.config.beta * metrics.constraint_violation
        )

        # ④ LOG — Record everything
        self.state.total_reward += obs.reward
        self.state.total_regret += metrics.regret
        self.state.step += 1
        self.state.metrics_history.append(metrics)

        return action

    def summary(self) -> dict[str, float]:
        """Summary statistics across all timesteps."""
        if not self.state.metrics_history:
            return {}

        h = self.state.metrics_history
        return {
            "steps": self.state.step,
            "total_reward": self.state.total_reward,
            "total_regret": self.state.total_regret,
            "avg_kl": sum(m.kl_divergence for m in h) / len(h),
            "avg_entropy": sum(m.belief_entropy for m in h) / len(h),
            "avg_risk": sum(m.risk_cvar for m in h) / len(h),
            "avg_constraint_violation": sum(m.constraint_violation for m in h) / len(h),
            "avg_J": sum(m.J for m in h) / len(h),
            "watchdog_interventions": self.state.watchdog_interventions,
            "final_mode": self.state.mode.name,
        }
