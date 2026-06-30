# [C5-REAL] Exergy-Maximized
"""Cortex Router v3 - Causal Policy Gradient System.

Optimizes routing decisions over future epistemic stability trajectories.
Updates policy weights via causal advantage (expected KL reduction).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from babylon60.router.policy import EpistemicPolicyNetwork, SignalVector

logger = logging.getLogger("cortex.router.causal")

ModelType = Literal["gemini-3.5-flash", "gemini-3.1-pro"]


@dataclass
class CausalTrajectory:
    """A sequence of routing events mapping decisions to future KL divergence."""

    state: SignalVector
    action: ModelType
    kl_divergence_post: float
    hazard_rate_impact: float


class CausalPolicyGradientRouter(EpistemicPolicyNetwork):
    """
    Learns 'which model reduces future KL divergence trajectories'.
    Implements a stability-optimal objective via policy gradient.
    """

    def __init__(self, temperature: float = 1.0, learning_rate: float = 0.01, gamma: float = 0.99):
        super().__init__(temperature)
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.trajectories: list[CausalTrajectory] = []

    def log_trajectory(self, trajectory: CausalTrajectory) -> None:
        """Accumulates experience buffer for causal reinforcement."""
        self.trajectories.append(trajectory)

    def _compute_causal_advantage(self, trajectory: CausalTrajectory) -> float:
        """
        Computes A(s, a).
        Reward is negative KL divergence penalty and hazard reduction.
        """
        # Stability reward: lower KL is better, lower hazard is better.
        reward = -(trajectory.kl_divergence_post) - (trajectory.hazard_rate_impact * 2.0)
        return reward

    def update_causal_policy(self) -> None:
        """
        Executes a policy gradient update step using REINFORCE.
        Objective: E[ A(s, a) * ∇_θ log π_θ(a | s) ]
        """
        if not self.trajectories:
            return

        logger.info(
            "[CAUSAL] Running policy gradient update over %d trajectories", len(self.trajectories)
        )

        for t in self.trajectories:
            # 1. Compute Advantage
            advantage = self._compute_causal_advantage(t)

            # 2. Forward pass to get probabilities
            probs = self.forward(t.state)
            action_idx = self.models.index(t.action)

            # 3. Causal log-probability gradient mapping
            # d(log_pi)/d(logit_i) = 1 - pi_i (for chosen action)
            grad_log_pi = 1.0 - probs[action_idx]

            # Policy Shift = α * A * grad
            policy_shift = self.learning_rate * advantage * grad_log_pi

            # Apply gradient shift directly to the action's bias layer (Simplified for C5-REAL pure Python)
            self.b2[action_idx] += policy_shift

            logger.debug(
                "Trajectory KL=%.3f, Advantage=%.3f, Shift=%.4f",
                t.kl_divergence_post,
                advantage,
                policy_shift,
            )

        # Flush buffer
        self.trajectories.clear()
        logger.info("[CAUSAL] Policy parameters updated. Future KL trajectories optimized.")
