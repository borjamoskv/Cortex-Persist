"""IDC Core Types — the data structures that define an agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np
from numpy.typing import NDArray


class AgentMode(Enum):
    """Operational mode of the agent."""
    NORMAL = auto()
    SAFE = auto()       # Watchdog triggered — conservative actions only
    EXPLORE = auto()    # Deliberately increasing uncertainty
    SHUTDOWN = auto()   # Fatal anomaly — stop everything


@dataclass
class Belief:
    """Probabilistic belief state b_t.

    For a discrete state space of size N, belief is a probability vector.
    For continuous domains, replace with particles/Gaussian/etc.
    """
    probabilities: NDArray[np.float64]  # shape (N,), sums to 1
    entropy: float = 0.0
    last_kl_update: float = 0.0  # KL(b_{t+1} || b_t) from last update
    calibration_error: float = 0.0

    def __post_init__(self) -> None:
        self.entropy = self._compute_entropy()

    def _compute_entropy(self) -> float:
        p = self.probabilities[self.probabilities > 0]
        return float(-np.sum(p * np.log2(p)))

    @classmethod
    def uniform(cls, n: int) -> Belief:
        return cls(probabilities=np.ones(n) / n)


@dataclass
class Action:
    """A candidate action with metadata."""
    index: int
    expected_utility: float = 0.0
    risk: float = 0.0              # CVaR or worst-case
    constraint_violation: float = 0.0  # max(0, g(x,a))
    is_safe: bool = True


@dataclass
class Observation:
    """What the agent perceives at time t."""
    state_index: int       # True state revealed (partially or fully)
    reward: float = 0.0
    is_terminal: bool = False


@dataclass
class Metrics:
    """IDC unified metrics for one timestep."""
    # Information layer
    kl_divergence: float = 0.0
    belief_entropy: float = 0.0
    prediction_error: float = 0.0
    calibration_error: float = 0.0

    # Decision layer
    expected_utility: float = 0.0
    regret: float = 0.0
    risk_cvar: float = 0.0
    exploration_ratio: float = 0.0

    # Control layer
    constraint_violation: float = 0.0
    stability_margin: float = 0.0
    drift_rate: float = 0.0

    # Watchdog
    ood_score: float = 0.0
    watchdog_interventions: int = 0

    # Composite
    J: float = 0.0  # The unified IDC objective


@dataclass
class AgentConfig:
    """Configuration knobs for the IDC agent."""
    alpha: float = 0.1      # Information penalty weight (KL cost)
    beta: float = 0.5       # Control penalty weight (constraint/stability)
    lambda_risk: float = 0.3  # Risk aversion in decision layer
    exploration_rate: float = 0.1  # epsilon for explore/exploit
    ood_threshold: float = 2.0    # Watchdog OOD trigger
    drift_threshold: float = 1.0  # Watchdog drift trigger
    max_constraint_violation: float = 0.01  # Hard safety limit
    horizon: int = 5              # MPC lookahead for control
