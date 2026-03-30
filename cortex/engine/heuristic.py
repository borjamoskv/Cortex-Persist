from abc import ABC, abstractmethod
from typing import Any


class HeuristicEngine(ABC):
    """
    Base interface for Neural/Symbolic Heuristic evaluations in PUCT MCTS.
    Predicts prior probabilities (P) and state value (V).
    """

    @abstractmethod
    async def predict(
        self, state: dict[str, Any], available_actions: list[str]
    ) -> tuple[dict[str, float], float]:
        """
        Returns:
            P: A dictionary mapping each action to its predicted prior probability.
            V: The predicted value of the state [-1.0, 1.0].
        """
        pass


class MockHeuristicEngine(HeuristicEngine):
    """
    Mock engine to test PUCT wiring without neural network overhead.
    Intentionally assigns a higher prior probability to 'rotate_90' to demonstrate pruning,
    proving that neural models can radically reduce the MCTS branching factor.
    """

    async def predict(
        self, state: dict[str, Any], available_actions: list[str]
    ) -> tuple[dict[str, float], float]:
        p = {}
        for action in available_actions:
            if action == "rotate_90":
                p[action] = 0.8
            else:
                p[action] = 0.2 / max(1, len(available_actions) - 1)

        # Return prior distribution and a neutral value
        return p, 0.0
