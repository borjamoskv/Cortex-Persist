"""
AlphaZero MCTS implementation for deterministic domain synthesis.
"""

import math
from typing import Any, Generic, TypeVar

from cortex.engine.alphazero.network import PolicyValueNetwork

State = TypeVar("State")
Action = TypeVar("Action")


class AlphaZeroNode(Generic[State, Action]):
    """Node in the AlphaZero MCTS tree."""

    def __init__(self, state: State, parent: "AlphaZeroNode[State, Action] | None" = None, action: Action | None = None, prior: float = 0.0):
        self.state = state
        self.parent = parent
        self.action = action  # Action that led to this node

        # Tree stats
        self.visit_count = 0
        self.value_sum = 0.0
        self.prior = prior
        self.children: dict[Action, "AlphaZeroNode[State, Action]"] = {}
        
        # MCTS State
        self.is_expanded = False

    @property
    def value(self) -> float:
        """Mean action value (Q)."""
        if self.visit_count == 0:
            return 0.0
        return self.value_sum / self.visit_count

    def expand(self, action_priors: dict[Action, float]) -> None:
        """Expand node with valid actions and their policy priors."""
        for action, prob in action_priors.items():
            if action not in self.children:
                # The environment translates action -> next_state later
                # For now, children store the edge. The exact state is computed on traversal.
                pass
        self.is_expanded = True


class MCTS(Generic[State, Action]):
    """
    Monte Carlo Tree Search with PUCT for AlphaZero.
    """

    def __init__(self, network: PolicyValueNetwork[State, Action], c_puct: float = 1.0, num_simulations: int = 50):
        self.network = network
        self.c_puct = c_puct
        self.num_simulations = num_simulations

    def ucb_score(self, parent: AlphaZeroNode[State, Action], child: AlphaZeroNode[State, Action]) -> float:
        """Calculate PUCT score for node selection."""
        pb_c = math.log((parent.visit_count + 19652 + 1) / 19652) + self.c_puct
        pb_c *= math.sqrt(parent.visit_count) / (child.visit_count + 1)
        prior_score = pb_c * child.prior
        value_score = child.value
        return value_score + prior_score

    def simulate(self, root: AlphaZeroNode[State, Action], env_step_fn) -> None:
        """Run self.num_simulations to build the tree and value estimates."""
        for _ in range(self.num_simulations):
            node = root
            search_path = [node]

            # 1. Selection
            while node.is_expanded and node.children:
                action, next_node = max(node.children.items(), key=lambda item: self.ucb_score(node, item[1]))
                node = next_node
                search_path.append(node)

            # 2. Evaluation
            # If the state represents a terminal node (win/loss), get true value.
            # Otherwise, evaluate with network.
            terminal_value = env_step_fn.get_terminal_value(node.state)
            if terminal_value is not None:
                value = terminal_value
            else:
                action_priors, value = self.network.evaluate(node.state)
                
                # 3. Expansion
                # Create child nodes for all legal actions
                legal_actions = env_step_fn.get_legal_actions(node.state)
                for action in legal_actions:
                    prior = action_priors.get(action, 0.0)
                    next_state = env_step_fn.step(node.state, action)
                    child = AlphaZeroNode(state=next_state, parent=node, action=action, prior=prior)
                    node.children[action] = child
                
                node.is_expanded = True

            # 4. Backpropagation
            self.backpropagate(search_path, value)

    def backpropagate(self, search_path: list[AlphaZeroNode[State, Action]], value: float) -> None:
        """Propagate value estimate up the search path."""
        # For zero-sum two-player, value alternates. For standard single-agent puzzle (ARC), value is direct.
        # Assuming single-agent puzzle mode for now.
        for node in reversed(search_path):
            node.value_sum += value
            node.visit_count += 1

    async def simulate_async(self, root: AlphaZeroNode[State, Action], env_step_fn) -> None:
        """Async version of simulate to support async LLM evaluators and envs."""
        for _ in range(self.num_simulations):
            node = root
            search_path = [node]

            while node.is_expanded and node.children:
                action, next_node = max(node.children.items(), key=lambda item: self.ucb_score(node, item[1]))
                node = next_node
                search_path.append(node)

            terminal_value = await env_step_fn.get_terminal_value_async(node.state)
            if terminal_value is not None:
                value = terminal_value
            else:
                action_priors, value = await self.network.evaluate_async(node.state)

                legal_actions = await env_step_fn.get_legal_actions_async(node.state)
                for action in legal_actions:
                    prior = action_priors.get(action, 0.0)
                    next_state = await env_step_fn.step_async(node.state, action)
                    child = AlphaZeroNode(state=next_state, parent=node, action=action, prior=prior)
                    node.children[action] = child

                node.is_expanded = True

            self.backpropagate(search_path, value)
        """Propagate value estimate up the search path."""
        # For zero-sum two-player, value alternates. For standard single-agent puzzle (ARC), value is direct.
        # Assuming single-agent puzzle mode for now.
        for node in reversed(search_path):
            node.value_sum += value
            node.visit_count += 1

    def get_action_probabilities(self, root: AlphaZeroNode[State, Action], temperature: float = 1.0) -> dict[Action, float]:
        """Compute the action probabilities based on visit counts."""
        action_visits = {action: child.visit_count for action, child in root.children.items()}
        
        if temperature == 0:
            # Deterministic: pick action with max visits
            best_action = max(action_visits.keys(), key=lambda a: action_visits[a])
            return {a: 1.0 if a == best_action else 0.0 for a in action_visits.keys()}
        
        # Stochastic interpretation
        action_probs = {}
        total = sum(v ** (1 / temperature) for v in action_visits.values())
        if total == 0:
            uniform = 1.0 / len(action_visits) if action_visits else 1.0
            return {a: uniform for a in action_visits.keys()}

        for action, visits in action_visits.items():
            action_probs[action] = (visits ** (1 / temperature)) / total
            
        return action_probs
