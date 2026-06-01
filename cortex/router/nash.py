"""Cortex Router v4 - Nash-Equilibrium Epistemic Router.

Implements a game-theoretic mixture-of-experts routing system where
Flash (execution optimizer) and Pro (epistemic stability optimizer)
act as players in a Bayesian routing game.
"""

from __future__ import annotations
import math
import logging
from dataclasses import dataclass
from typing import Literal

from cortex.router.causal import CausalTrajectory, CausalPolicyGradientRouter
from cortex.router.policy import SignalVector

logger = logging.getLogger("cortex.router.nash")

ModelType = Literal["gemini-3.5-flash", "gemini-3.1-pro"]

@dataclass
class RoutingUtilities:
    """Utilities for Nash Equilibrium evaluation."""
    u_flash: float
    u_pro: float

class NashCausalRouter(CausalPolicyGradientRouter):
    """
    Game-theoretic causal policy router.
    Evaluates U_F and U_P to find the routing equilibrium over the policy gradient.
    """
    def __init__(self, alpha: float = 0.5, beta: float = 1.0, gamma: float = 1.5, delta: float = 0.8):
        super().__init__()
        # Hyperparameters for Utility functions
        self.alpha = alpha  # latency penalty
        self.beta = beta    # kl penalty
        self.gamma = gamma  # correctness reward
        self.delta = delta  # misrouting risk

    def compute_utilities(self, state: SignalVector) -> RoutingUtilities:
        """
        Computes the utility matrices for Player 1 (Flash) and Player 2 (Pro).
        U_F = -alpha * expected_latency - beta * KL_instability
        U_P = +gamma * expected_correctness - delta * misrouting_risk
        """
        # Heuristic proxies for latency based on model priors
        expected_latency_f = 0.1  # Flash = Fast execution
        expected_latency_p = 1.0  # Pro = Slow reasoning
        
        # Flash Utility: Favors low latency, heavily penalized by high KL instability
        u_flash = -(self.alpha * expected_latency_f) - (self.beta * state.kl_instability)
        
        # Pro Utility: Favors complex states (where correctness matters more) penalized by low entropy
        expected_correctness = state.entropy_score + (state.ast_complexity / 100.0)
        misrouting_risk = max(0.0, 1.0 - state.kl_instability) # Penalty if routed to Pro for trivial tasks
        
        u_pro = (self.gamma * expected_correctness) - (self.delta * misrouting_risk)
        
        return RoutingUtilities(u_flash, u_pro)

    def route(self, state: SignalVector) -> ModelType:
        """
        Determines the route by approximating the Nash Equilibrium over the causal policy.
        """
        # 1. Base Causal Policy forward pass (learned bias)
        probs = self.forward(state)
        
        # 2. Compute Nash Utilities
        utilities = self.compute_utilities(state)
        
        logger.info("[NASH] Utilities - Flash: %.3f, Pro: %.3f", utilities.u_flash, utilities.u_pro)
        logger.info("[NASH] Policy Probabilities - Flash: %.3f, Pro: %.3f", probs[0], probs[1])
        
        # 3. Equilibrium constraint: no unilateral deviation
        # Combine structural utility with learned log-probability gradient
        effective_f = utilities.u_flash + math.log(probs[0] + 1e-9)
        effective_p = utilities.u_pro + math.log(probs[1] + 1e-9)
        
        # Override threshold check (v4 spec fallback override)
        if state.kl_instability > 2.0 or state.ast_complexity > 50 or state.entropy_score > 0.8:
            logger.info("[ROUTER] Threshold Override Triggered -> 3.1 Pro")
            return "gemini-3.1-pro"

        if effective_p > effective_f:
            logger.info("[ROUTER] Equilibrium reached -> 3.1 Pro")
            return "gemini-3.1-pro"
        else:
            logger.info("[ROUTER] Equilibrium reached -> 3.5 Flash")
            return "gemini-3.5-flash"
