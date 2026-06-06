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
            self.entropy_score,  # e_t
            self.cyclomatic_depth,
            self.event_rate,
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
            [-0.5, -0.5, -0.8, 0.5],  # Flash (favors execution/low entropy)
            [0.5, 0.5, 0.8, -0.5],  # Pro (favors semantic reasoning/high KL)
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

        probs = self._softmax(logits)

        # Cache forward state variables for backpropagation update
        self._last_x = x
        self._last_h = h
        self._last_probs = probs

        return probs

    def route(self, state: SignalVector) -> ModelType:
        """Stochastically sample model based on policy distribution."""
        probs = self.forward(state)
        logger.info("[POLICY] pi_theta(Flash|s_t)=%.3f, pi_theta(Pro|s_t)=%.3f", probs[0], probs[1])

        if random.random() < probs[0]:
            self._last_action = 0
            return self.models[0]
        self._last_action = 1
        return self.models[1]

    def update_policy(self, reward: float, learning_rate: float = 0.01):
        """
        Policy Gradient update step (REINFORCE).
        Updates parameters W1, b1, W2, b2 based on reward scalar.
        """
        if (
            not hasattr(self, "_last_probs")
            or not hasattr(self, "_last_action")
            or not hasattr(self, "_last_x")
            or not hasattr(self, "_last_h")
        ):
            logger.warning(
                "[POLICY] Attempted update_policy without stored forward pass/routing event."
            )
            return

        probs = self._last_probs
        action = self._last_action
        x = self._last_x
        h = self._last_h

        # Logits gradients: dL/dlogits_i = reward * (1 - probs[i]) if i == action else -reward * probs[i]
        d_logits = [0.0] * 2
        for i in range(2):
            if i == action:
                d_logits[i] = reward * (1.0 - probs[i])
            else:
                d_logits[i] = reward * (0.0 - probs[i])

        # Backpropagation:
        # W2 (2 experts x 4 hidden): dW2[i][j] = d_logits[i] * h[j]
        # b2 (2 biases): db2[i] = d_logits[i]
        # h (4 hidden): dh[j] = sum(d_logits[i] * W2[i][j] for i in range(2))
        dW2 = [[0.0] * 4 for _ in range(2)]
        db2 = [0.0] * 2
        dh = [0.0] * 4

        for i in range(2):
            db2[i] = d_logits[i]
            for j in range(4):
                dW2[i][j] = d_logits[i] * h[j]
                dh[j] += d_logits[i] * self.W2[i][j]

        # ReLU backprop: d_h_logits[j] = dh[j] if h[j] > 0 else 0
        d_h_logits = [0.0] * 4
        for j in range(4):
            if h[j] > 0.0:
                d_h_logits[j] = dh[j]

        # W1 (4 hidden x 5 inputs): dW1[j][k] = d_h_logits[j] * x[k]
        # b1 (4 biases): db1[j] = d_h_logits[j]
        dW1 = [[0.0] * 5 for _ in range(4)]
        db1 = [0.0] * 4

        for j in range(4):
            db1[j] = d_h_logits[j]
            for k in range(5):
                dW1[j][k] = d_h_logits[j] * x[k]

        # Parameter updates (Gradient Ascent for REINFORCE)
        for i in range(2):
            self.b2[i] += learning_rate * db2[i]
            for j in range(4):
                self.W2[i][j] += learning_rate * dW2[i][j]

        for j in range(4):
            self.b1[j] += learning_rate * db1[j]
            for k in range(5):
                self.W1[j][k] += learning_rate * dW1[j][k]

        # Clear cached trajectory values to prevent double updates
        del self._last_probs
        del self._last_action
        del self._last_x
        del self._last_h
