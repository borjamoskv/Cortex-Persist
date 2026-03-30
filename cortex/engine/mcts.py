"""
CORTEX MCTS (Test-Time Compute) — ARC-AGI-3 Active Inference Axiom (Ω_ACTIVE_INFERENCE).

This module implements the Active Inference Loop: instead of static zero-shot inference,
we generate synthetic rollouts, evaluate them locally (sandbox red team), and select
the path with highest net exergy / lowest vulnerability count.
"""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from cortex.engine.signals import log_limbic, log_motor

if TYPE_CHECKING:
    from cortex.engine.legion import SiegeResult


logger = logging.getLogger("cortex.engine.mcts")


__all__ = ["TestTimeComputeActuator", "MCTS_ACTUATOR"]


class MCTSNode:
    """MCTS MCTSNode representing a simulation state."""

    def __init__(
        self,
        state: Mapping[str, Any],
        intent: str,
        parent: MCTSNode | None = None,
        action: Any = None
    ):
        self.state = state
        self.intent = intent
        self.parent = parent
        self.action = action  # Action that led to this state
        self.children: list[MCTSNode] = []
        self.visits = 0
        self.value = 0.0
        self.vulnerabilities = 1_000_000

    def puct(self, parent_visits: int, c_puct: float = 2.0) -> float:
        """Calculate PUCT for node selection."""
        if self.visits == 0:
            return float("inf")
        log_parent_v = math.log10(max(parent_visits, 1))
        q = self.value / self.visits
        u = c_puct * math.sqrt(log_parent_v) / (1 + self.visits)
        return q + u

    def select_child_puct(self, c_puct: float = 2.0) -> MCTSNode:
        """Select child with highest PUCT."""
        return max(self.children, key=lambda n: n.puct(self.visits, c_puct))


class TestTimeComputeActuator:
    """
    Sovereign Kinetic Actuator for Active Inference.

    Implements a true Monte Carlo Tree Search over the LegionOmegaEngine.
    Trades TTFT for thermodynamic correctness and axiomatic convergence.
    """

    def __init__(self, legion=None, iterations: int = 10, batch_size: int = 3):
        if legion is None:
            from cortex.engine.legion import LEGION_OMEGA
            self.legion = LEGION_OMEGA
        else:
            self.legion = legion
        self.iterations = iterations
        self.batch_size = batch_size

    async def active_inference(self, intent: str, context: Mapping[str, Any]) -> SiegeResult:
        """
        Execute parallelized MCTS Test-Time Compute loop.
        """
        msg = (f"🚀 Iniciando MCTS Active Inference ({self.iterations} iters, "
               f"batch={self.batch_size})...")
        log_limbic(msg, source="MCTS", vibe="cterm-exergy")

        root = MCTSNode(state=context, intent=intent)
        best_result: SiegeResult | None = None
        min_vulns = 1_000_000

        # PUCT Hyperparameter (Exploration control)
        c_puct = 2.0

        # Adaptive Early Exit Tracker
        best_overall_exergy = 0.0
        plateau_counter = 0
        PLATEAU_PATIENCE = 3  # wait 3 batches before deciding plateau
        EXERGY_THRESHOLD_FOR_PLATEAU = 0.85

        for batch_idx in range(0, self.iterations, self.batch_size):
            # 1. Selection & Expansion (Generate a batch of leaf nodes)
            batch_tasks = []
            selected_nodes = []

            current_batch_size = min(self.batch_size, self.iterations - batch_idx)

            for i in range(current_batch_size):
                node = root
                # Tree traversal with PUCT logic
                while node.children:
                    node = node.select_child_puct(c_puct=c_puct)

                # Simulation parameters
                synthetic_context: dict[str, Any] = dict(node.state)
                synthetic_context["mcts_iteration"] = batch_idx + i
                synthetic_context["temperature_shift"] = 0.05 * float(batch_idx + i)

                selected_nodes.append(node)
                batch_tasks.append(self.legion.forge(intent, synthetic_context))

            # 2. Parallel Simulation (Forge Batch)
            log_motor(
                f"MCTS Batch {batch_idx//self.batch_size + 1} | Size: {len(batch_tasks)}",
                action="MCTS_BATCH_SIM",
                vibe="cterm-sys"
            )

            results = await asyncio.gather(*batch_tasks)

            # 3. Backpropagation for each result in batch
            for i, result in enumerate(results):
                leaf_node = selected_nodes[i]

                # Expansion
                new_node = MCTSNode(
                    state=leaf_node.state,
                    intent=intent,
                    parent=leaf_node,
                    action=result.final_code
                )
                leaf_node.children.append(new_node)

                # Reward calculation
                vulns = len(result.vulnerabilities) if result.vulnerabilities else 0
                reward = 0.05 + (result.exergy * 3.0)
                if result.success:
                    reward += 15.0
                elif vulns < min_vulns:
                    reward += 5.0
                if result.entropy_delta > 0:
                    reward += result.entropy_delta * 0.5

                # Backprop
                curr: MCTSNode | None = new_node
                while curr is not None:
                    curr.visits += 1
                    curr.value += reward
                    curr = curr.parent

                # Track best
                is_better_vulns = (result.final_code and vulns < min_vulns)
                is_better_exergy = (
                    best_result is None or
                    (vulns == min_vulns and result.exergy > best_result.exergy)
                )

                if result.success or is_better_vulns or is_better_exergy:
                    min_vulns = min(min_vulns, vulns)
                    best_result = result
                    if result.success and result.exergy > 0.98:
                        log_limbic("MCTS: Alta Exergía detectada. Early Exit.", source="MCTS")
                        return best_result

            # Adaptive Early Exit Check
            if best_result is not None:
                if best_result.exergy > best_overall_exergy + 0.01:
                    best_overall_exergy = best_result.exergy
                    plateau_counter = 0
                else:
                    plateau_counter += 1

                reached_patience = plateau_counter >= PLATEAU_PATIENCE
                exergy_high_enough = best_overall_exergy >= EXERGY_THRESHOLD_FOR_PLATEAU

                if reached_patience and exergy_high_enough:
                    msg = f"MCTS: Exergy plateau reached ({best_overall_exergy:.2f}). Early Exit."
                    log_limbic(msg, source="MCTS")
                    return best_result

            await asyncio.sleep(0.01)

        return best_result or SiegeResult(
            success=False,
            final_code="",
            cycles=self.iterations,
            vulnerabilities=["MCTS_FAILED_TO_CONVERGE"]
        )


class KineticActuator(TestTimeComputeActuator):
    """Alias for TestTimeComputeActuator specializing in Kinetic Common Sense."""
    pass


# Global singleton for Active Inference
MCTS_ACTUATOR = TestTimeComputeActuator()
KINETIC_ACTUATOR = KineticActuator()
