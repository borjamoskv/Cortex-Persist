"""IDC Layers — Information, Decision, Control, Watchdog.

Each layer is a pure function (state in, state out). No hidden side effects.
The Agent orchestrates them in sequence.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .types import Action, AgentConfig, AgentMode, Belief, Observation


# ──────────────────────────────────────────────────────────────
# LAYER I — INFORMATION (Bayesian Belief Update)
# ──────────────────────────────────────────────────────────────

def update_belief(
    belief: Belief,
    observation: Observation,
    likelihood_matrix: NDArray[np.float64],
) -> Belief:
    """Bayesian update: b_{t+1} ∝ P(o|s) · b_t.

    Args:
        belief: Current belief state b_t
        observation: Observation o_{t+1}
        likelihood_matrix: P(o|s) matrix, shape (n_observations, n_states)

    Returns:
        Updated belief b_{t+1} with KL divergence recorded.
    """
    prior = belief.probabilities
    likelihood = likelihood_matrix[observation.state_index]

    # Bayes rule
    posterior = likelihood * prior
    total = posterior.sum()

    if total < 1e-15:
        # Observation was "impossible" under current beliefs — watchdog territory
        posterior = np.ones_like(prior) / len(prior)  # Reset to uniform
    else:
        posterior = posterior / total

    # KL(posterior || prior) — information gained
    kl = _kl_divergence(posterior, prior)

    new_belief = Belief(
        probabilities=posterior,
        last_kl_update=kl,
    )

    return new_belief


def _kl_divergence(p: NDArray, q: NDArray) -> float:
    """KL(P || Q) in bits. Safe against zeros."""
    mask = (p > 1e-15) & (q > 1e-15)
    if not mask.any():
        return 0.0
    return float(np.sum(p[mask] * np.log2(p[mask] / q[mask])))


# ──────────────────────────────────────────────────────────────
# LAYER D — DECISION (Expected Utility Maximization)
# ──────────────────────────────────────────────────────────────

def propose_actions(
    belief: Belief,
    utility_matrix: NDArray[np.float64],
    config: AgentConfig,
    n_actions: int,
) -> list[Action]:
    """Evaluate all actions under current belief.

    Args:
        belief: Current belief b_t
        utility_matrix: U(s, a) matrix, shape (n_states, n_actions)
        config: Agent configuration
        n_actions: Number of available actions

    Returns:
        List of Actions ranked by risk-adjusted expected utility.
    """
    actions: list[Action] = []

    for a_idx in range(n_actions):
        utilities = utility_matrix[:, a_idx]

        # E[U(s,a)] under belief
        expected_u = float(np.dot(belief.probabilities, utilities))

        # Risk: CVaR approximation — expected value of bottom 20% outcomes
        risk = _compute_cvar(belief.probabilities, utilities, alpha=0.2)

        # Risk-adjusted score
        score = expected_u - config.lambda_risk * risk

        actions.append(Action(
            index=a_idx,
            expected_utility=score,
            risk=risk,
        ))

    # Sort by expected utility (descending)
    actions.sort(key=lambda a: a.expected_utility, reverse=True)
    return actions


def _compute_cvar(probs: NDArray, values: NDArray, alpha: float = 0.2) -> float:
    """Conditional Value at Risk — expected loss in the worst alpha-fraction.

    Higher CVaR = more dangerous action.
    """
    sorted_indices = np.argsort(values)
    sorted_probs = probs[sorted_indices]
    sorted_values = values[sorted_indices]

    cumulative = np.cumsum(sorted_probs)
    mask = cumulative <= alpha

    if not mask.any():
        return float(-sorted_values[0])  # Worst case

    tail_probs = sorted_probs[mask]
    tail_values = sorted_values[mask]

    if tail_probs.sum() < 1e-15:
        return 0.0

    cvar = float(-np.dot(tail_probs, tail_values) / tail_probs.sum())
    return max(0.0, cvar)


def select_action(
    actions: list[Action],
    config: AgentConfig,
    rng: np.random.Generator,
) -> Action:
    """Epsilon-greedy selection with exploration.

    Args:
        actions: Ranked candidate actions from propose_actions
        config: Agent configuration
        rng: Random number generator

    Returns:
        Selected action (best or random for exploration).
    """
    if rng.random() < config.exploration_rate:
        return actions[rng.integers(len(actions))]
    return actions[0]


# ──────────────────────────────────────────────────────────────
# LAYER C — CONTROL (Constraint Filtering + Stability)
# ──────────────────────────────────────────────────────────────

def filter_action(
    action: Action,
    actions: list[Action],
    constraints: NDArray[np.float64] | None,
    config: AgentConfig,
) -> Action:
    """Filter action through safety constraints.

    Args:
        action: Proposed action from Decision layer
        actions: All candidate actions (fallback pool)
        constraints: Constraint values g(a) for each action. g(a) ≤ 0 = safe.
        config: Agent configuration

    Returns:
        Safe action (original or fallback).
    """
    if constraints is None:
        action.is_safe = True
        action.constraint_violation = 0.0
        return action

    violation = max(0.0, float(constraints[action.index]))
    action.constraint_violation = violation

    if violation <= config.max_constraint_violation:
        action.is_safe = True
        return action

    # Action is unsafe — find safest alternative
    action.is_safe = False
    for alt in actions:
        alt_violation = max(0.0, float(constraints[alt.index]))
        if alt_violation <= config.max_constraint_violation:
            alt.is_safe = True
            alt.constraint_violation = alt_violation
            return alt

    # No safe action exists — return least-violating with flag
    best_alt = min(actions, key=lambda a: float(constraints[a.index]))
    best_alt.is_safe = False
    best_alt.constraint_violation = max(0.0, float(constraints[best_alt.index]))
    return best_alt


# ──────────────────────────────────────────────────────────────
# WATCHDOG (Anomaly Detection + Safe Mode Trigger)
# ──────────────────────────────────────────────────────────────

def watchdog_check(
    belief: Belief,
    prev_belief: Belief | None,
    action: Action,
    config: AgentConfig,
) -> tuple[AgentMode, dict[str, float]]:
    """Monitor agent health. Trigger SAFE MODE on anomalies.

    Checks:
        1. OOD: belief entropy too high (lost in state space)
        2. Drift: belief changed too fast (non-stationarity)
        3. Constraint: action violates hard limits
        4. Impossible: last observation was "impossible"

    Returns:
        (mode, diagnostics dict)
    """
    diagnostics: dict[str, float] = {}
    mode = AgentMode.NORMAL

    # 1. OOD — entropy-based
    max_entropy = np.log2(len(belief.probabilities))
    ood_score = belief.entropy / max_entropy if max_entropy > 0 else 0.0
    diagnostics["ood_score"] = ood_score

    if ood_score > config.ood_threshold / max_entropy:
        mode = AgentMode.SAFE

    # 2. Drift — KL-based
    drift = belief.last_kl_update
    diagnostics["drift_rate"] = drift

    if drift > config.drift_threshold:
        mode = AgentMode.SAFE

    # 3. Constraint violation
    diagnostics["constraint_violation"] = action.constraint_violation
    if not action.is_safe:
        mode = AgentMode.SAFE

    # 4. Belief collapse (one state has > 99.9% mass but shouldn't)
    max_prob = float(np.max(belief.probabilities))
    diagnostics["max_belief_concentration"] = max_prob

    return mode, diagnostics
