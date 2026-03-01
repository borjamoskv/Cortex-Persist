import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Callable

@dataclass
class AgentState:
    """Represents the agent's internal belief and parameters."""
    belief: np.ndarray  # Probability distribution over states
    entropy: float      # H(X)
    stability_margin: float # Lyapunov/Safety margin
    last_observation: Any = None

class InformationEngine:
    """
    Base Epistemological Layer.
    Quantifies what the agent knows and ignores.
    """
    def __init__(self, num_states: int):
        self.num_states = num_states
        # Prior: Maximum Entropy (Uniform distribution)
        self.belief = np.ones(num_states) / num_states

    def update(self, observation: int, likelihood_matrix: np.ndarray) -> float:
        """
        Bayesian update: P(H|D) ∝ P(D|H) * P(H)
        Returns: Information Gain (KL Divergence from old to new belief)
        """
        old_belief = self.belief.copy()
        
        # Likelihood of this observation given each hidden state
        likelihood = likelihood_matrix[observation, :]
        
        # P(H|D)
        new_belief = likelihood * self.belief
        new_belief /= np.sum(new_belief) + 1e-12 # Normalize
        
        self.belief = new_belief
        
        # Calculate KL Divergence: D_KL(P || Q)
        kl = np.sum(new_belief * np.log((new_belief + 1e-12) / (old_belief + 1e-12)))
        return float(kl)

    @property
    def entropy(self) -> float:
        """H(X) = -Σ p(x) log p(x)"""
        return float(-np.sum(self.belief * np.log(self.belief + 1e-12)))

class DecisionEngine:
    """
    The 'Motor'. Converts Belief -> Action.
    Balances Exploration (Info Gain) vs Explotation (Utility).
    """
    def __init__(self, num_actions: int):
        self.num_actions = num_actions

    def choose_action(self, belief: np.ndarray, utility_matrix: np.ndarray, strategy: str = "thompson") -> int:
        """
        Implements Expected Utility Maximization.
        a* = argmax_a 𝔼[U(a, θ)]
        """
        # Expected utility for each action: Σ_s P(s) * U(a, s)
        expected_utilities = np.dot(utility_matrix, belief)
        
        if strategy == "greedy":
            return int(np.argmax(expected_utilities))
        elif strategy == "thompson":
            # Simple Thompson: add noise proportional to uncertainty (simplified)
            noise = np.random.normal(0, 0.1, size=self.num_actions)
            return int(np.argmax(expected_utilities + noise))
        
        return int(np.argmax(expected_utilities))

class ControlEngine:
    """
    The Stabilizer. Ensures behavior is bounded and robust.
    """
    def __init__(self, constraints: List[Callable]):
        self.constraints = constraints
        self.stability_margin = 1.0

    def validate_action(self, action: int, current_state: Any) -> bool:
        """
        Check if action violates constraints or stability margins.
        """
        for constraint in self.constraints:
            if not constraint(action, current_state):
                self.stability_margin *= 0.9 # Decreasing margin on violation
                return False
        
        self.stability_margin = min(1.0, self.stability_margin * 1.05)
        return True

class IDCAgent:
    """
    The Unified IDC Agent.
    Unifies Information, Decision, and Control.
    """
    def __init__(self, num_states: int, num_actions: int, constraints: List[Callable]):
        self.info = InformationEngine(num_states)
        self.decision = DecisionEngine(num_actions)
        self.control = ControlEngine(constraints)

    def step(self, observation: int, likelihood_matrix: np.ndarray, utility_matrix: np.ndarray) -> int:
        """
        The IDC Loop:
        1. Infer (Update Belief)
        2. Decide (Select Policy)
        3. Control (Validate Stability)
        """
        # 1. Information Layer
        info_gain = self.info.update(observation, likelihood_matrix)
        
        # 2. Decision Layer
        proposed_action = self.decision.choose_action(self.info.belief, utility_matrix)
        
        # 3. Control Layer
        if self.control.validate_action(proposed_action, self.info.belief):
            return proposed_action
        else:
            # Fallback to safe action (index 0 by convention)
            return 0

if __name__ == "__main__":
    # Quick sanity check
    agent = IDCAgent(num_states=3, num_actions=2, constraints=[lambda a, s: True])
    
    # 3 states (Low, Mid, High), 2 actions (Wait, Move)
    L = np.array([
        [0.8, 0.1, 0.1], # Obs 0 likely in State 0
        [0.1, 0.8, 0.1], # Obs 1 likely in State 1
        [0.1, 0.1, 0.8]  # Obs 2 likely in State 2
    ])
    
    U = np.array([
        [1.0, 0.5, 0.0], # Action 0 Utility per state
        [0.0, 0.5, 1.0]  # Action 1 Utility per state
    ])
    
    action = agent.step(observation=2, likelihood_matrix=L, utility_matrix=U)
    print(f"IDC Agent Action: {action} | Entropy: {agent.info.entropy:.4f}")
