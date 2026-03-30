"""
Policy & Value Network Protocol for AlphaZero.
"""

from typing import Generic, Protocol, TypeVar

State = TypeVar("State")
Action = TypeVar("Action")


class PolicyValueNetwork(Protocol[State, Action]):
    """
    Protocol defining the Neural Network interface for AlphaZero.
    Must output action priors (Policy) and board state value (Value).
    """

    def evaluate(self, state: State) -> tuple[dict[Action, float], float]:
        """
        Evaluate the state.
        
        Returns:
            action_priors: Dictionary mapping legal Actions to probability [0, 1].
            value: Estimated value of the state [-1, 1].
        """
        ...


class LocalHeuristicNetwork(Generic[State, Action]):
    """
    Sovereign local heuristic to bypass SaaS LLM dependency during test/training.
    Returns uniform priors and a zero-sum value baseline to force MCTS depth.
    """

    def __init__(self, env_step_fn):
        self.env_step_fn = env_step_fn

    def evaluate(self, state: State) -> tuple[dict[Action, float], float]:
        """
        Mock evaluation:
        - Uniform random policy over legal actions.
        - Value = +0.0 (Uncertain) unless trivially solvable.
        """
        legal_actions = self.env_step_fn.get_legal_actions(state)
        if not legal_actions:
            return {}, -1.0
            
        prob = 1.0 / len(legal_actions)
        priors = {action: prob for action in legal_actions}
        
        return priors, 0.0
