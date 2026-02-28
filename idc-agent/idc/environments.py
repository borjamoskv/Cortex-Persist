"""Toy Environments for IDC Agent demonstrations.

Each environment is a simple MDP/POMDP with:
- likelihood_matrix: P(o|s) — observation model
- utility_matrix: U(s,a) — reward structure
- constraints: g(a) — action constraints
- transition dynamics
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .types import Observation


@dataclass
class Environment:
    """Generic environment interface."""
    n_states: int
    n_actions: int
    n_observations: int
    likelihood: NDArray[np.float64]   # P(o|s): (n_obs, n_states)
    utility: NDArray[np.float64]      # U(s,a): (n_states, n_actions)
    constraints: NDArray[np.float64]  # g(a): (n_actions,)
    transition: NDArray[np.float64]   # P(s'|s,a): (n_states, n_actions, n_states)
    true_state: int = 0

    def reset(self, rng: np.random.Generator) -> Observation:
        self.true_state = rng.integers(self.n_states)
        obs_probs = self.likelihood[:, self.true_state]
        obs = rng.choice(self.n_observations, p=obs_probs)
        return Observation(state_index=obs, reward=0.0)

    def step(self, action_idx: int, rng: np.random.Generator) -> Observation:
        reward = float(self.utility[self.true_state, action_idx])

        # Transition
        trans_probs = self.transition[self.true_state, action_idx]
        self.true_state = rng.choice(self.n_states, p=trans_probs)

        # Noisy observation
        obs_probs = self.likelihood[:, self.true_state]
        obs = rng.choice(self.n_observations, p=obs_probs)

        return Observation(state_index=obs, reward=reward)


def make_risky_bandit() -> Environment:
    """3-state, 3-action problem with risk/safety tradeoffs.

    States:
        0: CALM market — safe actions pay decent
        1: VOLATILE market — risky actions pay big OR lose big
        2: CRASH market — everything hurts, only "hedge" survives

    Actions:
        0: SAFE (low return, always ok)
        1: RISKY (high return in calm/volatile, terrible in crash)
        2: HEDGE (moderate always, protected in crash)

    Observations: noisy version of true state (80% accurate).
    Constraint: Action 1 (RISKY) is penalized — g(1) > 0.
    """
    n_s, n_a, n_o = 3, 3, 3

    # P(o|s) — 80% accurate observation
    likelihood = np.array([
        [0.80, 0.10, 0.10],  # o=0 given s
        [0.10, 0.80, 0.10],  # o=1 given s
        [0.10, 0.10, 0.80],  # o=2 given s
    ], dtype=np.float64)

    # U(s, a) — The payoff matrix
    utility = np.array([
        # SAFE  RISKY  HEDGE
        [ 3.0,   8.0,   4.0],   # CALM
        [ 2.0,  12.0,   5.0],   # VOLATILE
        [ 1.0, -15.0,   6.0],   # CRASH
    ], dtype=np.float64)

    # g(a) ≤ 0 means safe. Action 1 (RISKY) violates constraint.
    constraints = np.array([-1.0, 0.5, -0.5], dtype=np.float64)

    # Transition P(s'|s,a) — simplified: action affects market stability
    transition = np.zeros((n_s, n_a, n_s), dtype=np.float64)

    # From CALM
    transition[0, 0] = [0.70, 0.25, 0.05]  # SAFE keeps calm
    transition[0, 1] = [0.40, 0.40, 0.20]  # RISKY destabilizes
    transition[0, 2] = [0.60, 0.30, 0.10]  # HEDGE moderate

    # From VOLATILE
    transition[1, 0] = [0.30, 0.50, 0.20]  # SAFE helps stabilize
    transition[1, 1] = [0.20, 0.40, 0.40]  # RISKY → more chaos
    transition[1, 2] = [0.25, 0.45, 0.30]  # HEDGE moderate

    # From CRASH
    transition[2, 0] = [0.20, 0.40, 0.40]  # SAFE slow recovery
    transition[2, 1] = [0.10, 0.30, 0.60]  # RISKY → deeper hole
    transition[2, 2] = [0.30, 0.40, 0.30]  # HEDGE best recovery

    return Environment(
        n_states=n_s,
        n_actions=n_a,
        n_observations=n_o,
        likelihood=likelihood,
        utility=utility,
        constraints=constraints,
        transition=transition,
    )


def make_information_foraging() -> Environment:
    """5-state env where gathering information is the key strategy.

    The agent must figure out which state it's in before acting.
    States 0-3 each have ONE good action; acting without knowing = regret.
    State 4 is "trap" — every action is bad, only early detection saves you.

    Tests: VOI, exploration, calibration.
    """
    n_s, n_a, n_o = 5, 4, 5

    # P(o|s) — 60% accurate (deliberate noise to test inference)
    likelihood = np.eye(n_o, n_s) * 0.50
    likelihood += 0.50 / n_s
    # Normalize columns to sum to 1
    likelihood = likelihood / likelihood.sum(axis=0, keepdims=True)

    # U(s, a) — each state rewards a different action
    utility = np.array([
        # a0    a1    a2    a3
        [10.0, -2.0, -2.0, -2.0],  # s0 → a0 is correct
        [-2.0, 10.0, -2.0, -2.0],  # s1 → a1 is correct
        [-2.0, -2.0, 10.0, -2.0],  # s2 → a2 is correct
        [-2.0, -2.0, -2.0, 10.0],  # s3 → a3 is correct
        [-5.0, -5.0, -5.0, -5.0],  # s4 → TRAP (all bad)
    ], dtype=np.float64)

    # No hard constraints in this env — pure info/decision challenge
    constraints = np.array([-1.0, -1.0, -1.0, -1.0], dtype=np.float64)

    # Transition: mostly stationary, small drift
    transition = np.zeros((n_s, n_a, n_s), dtype=np.float64)
    for s in range(n_s):
        for a in range(n_a):
            transition[s, a] = np.ones(n_s) * 0.05
            transition[s, a, s] = 0.80  # Mostly stays

    return Environment(
        n_states=n_s,
        n_actions=n_a,
        n_observations=n_o,
        likelihood=likelihood,
        utility=utility,
        constraints=constraints,
        transition=transition,
    )
