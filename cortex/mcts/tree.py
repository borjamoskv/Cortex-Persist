# [C5-REAL] Exergy-Maximized
"""MCTS Central Algorithm (CORTEX Chronos).

Implements Monte Carlo Tree Search to navigate the code mutations space.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

from cortex.extensions.llm.router import CortexLLMRouter
from cortex.mcts.git_env import MCTSGitEnvironment

logger = logging.getLogger("cortex.mcts.tree")


@dataclass
class MCTSNode:
    """Node in the quantum Git tree."""

    state_id: str
    mutation_prompt: str
    parent: MCTSNode | None = None
    children: list[MCTSNode] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0
    is_terminal: bool = False

    def add_child(self, child_state: str, prompt: str) -> MCTSNode:
        child = MCTSNode(state_id=child_state, mutation_prompt=prompt, parent=self)
        self.children.append(child)
        return child

    def uct(self, exploration_weight: float = 1.414) -> float:
        """Körner-UCT o Upper Confidence Bound for Trees."""
        if self.visits == 0:
            return float("inf")

        exploitation = self.value / self.visits
        exploration = (
            exploration_weight * math.sqrt(math.log(self.parent.visits) / self.visits)
            if self.parent
            else 0
        )
        return exploitation + exploration


class MCTSEngine:
    """MCTS-Git Quantum Engine."""

    def __init__(self, target_file: str, router: CortexLLMRouter) -> None:
        self.target_file = Path(target_file)
        self.router = router
        self.env = MCTSGitEnvironment(self.router, self.target_file)

    async def run(
        self, max_iterations: int = 10, mutation_str: str = "Refactor to O(1) syntax"
    ) -> str:
        """
        Starts the quantum traversal.

        Returns the name of the winning branch with maximum exergy.
        """
        base_branch = await self.env.get_current_branch()
        root = MCTSNode(state_id=f"{base_branch}-0", mutation_prompt=mutation_str)

        logger.info(
            "🌌 [CHRONOS] Starting MCTS Singularity (%d iterations) on %s",
            max_iterations,
            self.target_file.name,
        )

        for i in range(max_iterations):
            logger.debug("MCTS Iteration %d/%d", i + 1, max_iterations)

            # 1. Selection & Expansion
            node = root
            # Mock simplistic expansion logic for P0
            if not node.children:
                node.add_child(
                    f"{base_branch}-{i}-A",
                    "Refactor for pure thermodynamic efficiency and low memory overhead.",
                )
                node.add_child(
                    f"{base_branch}-{i}-B",
                    "Rewrite using modern Python 3.10+ async features strictly.",
                )
                node.add_child(
                    f"{base_branch}-{i}-C",
                    "Minimize line count without losing intent. O(1) mindset.",
                )

            # Pick best UCT child
            node = max(node.children, key=lambda n: n.uct())

            # 2. Emulate environment state
            await self.env.branch_out(base_branch, node.state_id)

            # 3. Simulation
            mutated = await self.env.mutate(node.mutation_prompt)
            if mutated:
                reward = await self.env.simulate()
            else:
                reward = 0.0

            # 4. Backpropagation
            node.visits += 1
            node.value += reward
            if node.parent:
                node.parent.visits += 1
                node.parent.value += reward

            # Restore main branch for the next state (Prevents destructive collapse)
            await self.env.secure_checkout(base_branch)

        # Select the optimal branch based on exploitation (average value)
        if not root.children:
            logger.warning("No nodes were expanded. Staying on base branch.")
            return base_branch

        best_node = max(root.children, key=lambda n: (n.value / n.visits) if n.visits > 0 else -1)
        best_branch = f"chronos/node-{best_node.state_id}"

        if best_node.visits > 0 and (best_node.value / best_node.visits) > 0:
            logger.info(
                "👑 [CHRONOS] Collapsed Reality: %s (Reward: %.2f)",
                best_branch,
                best_node.value / best_node.visits,
            )
            return best_branch
        logger.warning(
            "💀 [CHRONOS] No timelines passed the tests. Local extinction declared."
        )
        return base_branch
