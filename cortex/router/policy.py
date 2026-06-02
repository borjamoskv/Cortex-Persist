"""Cortex Router v2 - Differentiable Policy Network.

Implements a trainable MoE-style router evaluating the epistemic state vector
(AST complexity, KL instability, entropy, cyclomatic depth, event rate)
to output a stochastic routing distribution via softmax.
"""

from __future__ import annotations
import math
import random
import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger("cortex.router.policy")

ModelType = Literal["gemini-3.5-flash", "gemini-3.1-pro"]

@dataclass
class SignalVector:
    """Epistemic state vector (s_t)"""
    ast_complexity: float
    kl_instability: float
    entropy_score: float
    cyclomatic_depth: float
    event_rate: float
    
    def to_tensor(self) -> list[float]:
        return [
            math.log1p(self.ast_complexity),  # a_t = log(1 + AST)
            math.log1p(self.kl_instability),  # k_t = log(1 + KL)
            self.entropy_score,               # e_t
            self.cyclomatic_depth,
            self.event_rate
        ]

class EpistemicPolicyNetwork:
    """
    2-Expert MoE router with epistemic state-conditioned routing.
    Outputs a probability distribution over the model layer.
    """
    def __init__(self, temperature: float = 1.0):
        self.temperature = temperature
        
        # W1: 5 inputs -> 4 hidden units (initialized for baseline heuristic emulation)
        self.W1 = [
            [0.1, 0.5, 0.8, 0.2, 0.1],
            [-0.2, 0.4, 0.6, 0.1, 0.3],
            [0.0, 0.7, 0.9, 0.3, 0.4],
            [0.1, 0.1, 0.2, 0.8, 0.5],
        ]
        self.b1 = [0.0, 0.0, 0.0, 0.0]
        
        # W2: 4 hidden units -> 2 outputs (Flash, Pro)
        self.W2 = [
            [-0.5, -0.5, -0.8, 0.5], # Flash (favors execution/low entropy)
            [0.5, 0.5, 0.8, -0.5],   # Pro (favors semantic reasoning/high KL)
        ]
        self.b2 = [0.0, 0.0]
        
        self.models: list[ModelType] = ["gemini-3.5-flash", "gemini-3.1-pro"]

    def _relu(self, x: float) -> float:
        return max(0.0, x)
        
    def _softmax(self, logits: list[float]) -> list[float]:
        scaled = [val / self.temperature for val in logits]
        max_val = max(scaled)
        exp_vals = [math.exp(val - max_val) for val in scaled]
        sum_exp = sum(exp_vals)
        return [e / sum_exp for e in exp_vals]

    def forward(self, state: SignalVector) -> list[float]:
        """Compute pi_theta(m | s_t)."""
        x = state.to_tensor()
        
        # Hidden layer: h = ReLU(W1 * s_t + b1)
        h = [0.0] * 4
        for i in range(4):
            val = sum(self.W1[i][j] * x[j] for j in range(5)) + self.b1[i]
            h[i] = self._relu(val)
            
        # Logits layer: logits = W2 * h + b2
        logits = [0.0] * 2
        for i in range(2):
            logits[i] = sum(self.W2[i][j] * h[j] for j in range(4)) + self.b2[i]
            
        return self._softmax(logits)

    def route(self, state: SignalVector) -> ModelType:
        """Stochastically sample model based on policy distribution."""
        probs = self.forward(state)
        logger.info("[POLICY] pi_theta(Flash|s_t)=%.3f, pi_theta(Pro|s_t)=%.3f", probs[0], probs[1])
        
        if random.random() < probs[0]:
            return self.models[0]
        return self.models[1]

    def update_policy(self, reward: float):
        """
        Policy Gradient update step (REINFORCE placeholder).
        L_policy = -E[ R(s_t, m_t) ]
        R = α*F1 - β*KL - γ*entropy_instability - δ*routing_cost
        """
        # TODO: Implement backprop over W1, b1, W2, b2 based on reward scalar
        pass
