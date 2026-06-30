# [C5-REAL] Exergy-Maximized
"""MCTS Central Algorithm (CORTEX Chronos).

Implements Monte Carlo Tree Search to navigate the code mutations space.
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

from babylon60.extensions.llm.router import CortexLLMRouter
from babylon60.mcts.git_env import MCTSGitEnvironment

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

            # 1. Selection (OP_MCTS_SELECT)
            node = root
            while node.children and all(c.visits > 0 for c in node.children):
                node = max(node.children, key=lambda n: n.uct())

            # 2. Expansion (OP_MCTS_EXPAND)
            if not node.children and not node.is_terminal:
                strategies = [
                    f"{node.mutation_prompt} -> [Vector Alpha: Enforce O(1) time complexity and strict type boundaries]",
                    f"{node.mutation_prompt} -> [Vector Beta: Optimize thermodynamic Exergy, purge redundant logic]",
                    f"{node.mutation_prompt} -> [Vector Gamma: Maximize async resilience and fail-fast invariants]"
                ]
                for idx, strategy in enumerate(strategies):
                    node.add_child(f"{node.state_id}-{idx}", strategy)

            # 3. Parallel Asynchronous Evaluation (OP_ASYNC_GATHER)
            # Find all unvisited children to evaluate in parallel
            unvisited_children = [c for c in node.children if c.visits == 0]
            if not unvisited_children:
                # If all were visited (should not happen if we selected an expandable node), just break out
                unvisited_children = [max(node.children, key=lambda n: n.uct())]

            async def evaluate_child(child: MCTSNode) -> None:
                # Apply Virtual Loss (VAD)
                virtual_loss = 1.0
                child.visits += 1
                child.value -= virtual_loss
                
                parent_branch = base_branch
                if child.parent and child.parent != root:
                    parent_branch = f"chronos/node-{child.parent.state_id}"
                
                # OP_GIT_MULTIVERSE (creates Git Worktree)
                await self.env.branch_out(parent_branch, child.state_id)
                
                # OP_DETERMINISTIC_SIM
                mutated = await self.env.mutate(child.state_id, child.mutation_prompt)
                if mutated:
                    reward = await self.env.simulate(child.state_id)
                    if reward == 0.0:
                        child.is_terminal = True
                else:
                    reward = 0.0
                    child.is_terminal = True
                    
                # OP_BACKPROPAGATE
                # Remove virtual loss and add actual reward
                curr = child
                while curr is not None:
                    if curr == child:
                        curr.value += (reward + virtual_loss)
                    else:
                        curr.visits += 1
                        curr.value += reward
                    curr = curr.parent

                # OP_LOCAL_EXTINCTION (removes Git Worktree)
                await self.env.secure_checkout(child.state_id)

            logger.info("⚡ [CHRONOS] Initiating parallel evaluation for %d nodes...", len(unvisited_children))
            await asyncio.gather(*(evaluate_child(c) for c in unvisited_children))

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
