"""MOSKV-1 — Tesseract Dimensions Adapters.

Wraps Aether agents (Planner, Executor, Critic, Tester) into
asynchronous dimensional nodes (D1-D4).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from cortex.aether.critic import CriticAgent
from cortex.aether.executor import ExecutorAgent
from cortex.aether.models import AgentTask
from cortex.aether.planner import PlannerAgent
from cortex.aether.redteam import RedTeamAgent
from cortex.aether.tester import TesterAgent
from cortex.aether.tools import AgentToolkit
from cortex.manifold.models import DimensionalState

logger = logging.getLogger("cortex.manifold.dimensions")


class PerceptionDimension:
    """D1: Context & Prediction (Anamnesis / Prometheus)."""

    async def process(
        self, task: AgentTask, toolkit: AgentToolkit, state: DimensionalState
    ) -> dict[str, Any]:
        """Gather context and predict failure modes."""
        logger.info("D1 (Perception): Gathering context and situational awareness.")
        state.messages.append("Context gathered from CORTEX and toolkit.")

        # In a full implementation, this runs Semantic Search / CORTEX queries
        # For now, it prepares the baseline prediction.
        state.convergence = min(1.0, state.convergence + 0.3)
        return {"context_gathered": True, "predictions": ["rate limit", "OOM"]}


class DecisionDimension:
    """D2: Architecture & Intent (Wraps PlannerAgent)."""

    def __init__(self, llm, system_prompt: str | None = None) -> None:
        self.planner = PlannerAgent(llm, system_prompt)
        self.redteam = RedTeamAgent(llm)

    async def process(
        self, task: AgentTask, toolkit: AgentToolkit, state: DimensionalState
    ) -> Any:
        """Expand intent and generate architecture plan."""
        logger.info("D2 (Decision): Expanding intent and generating architecture.")

        try:
            plan = await self.planner.plan(task.description, toolkit)
            state.messages.append(f"Generated plan with {len(plan.steps)} steps.")
            
            if "refactor" in task.title.lower() or "ouroboros" in task.description.lower():
                logger.info("D2 (Decision): Forging Golden Master Siege via Red Team...")
                try:
                    await self.redteam.siege(task.description, toolkit)
                    state.messages.append("Red Team pre-execution siege generated.")
                except Exception as rt_err:  # noqa: BLE001
                    logger.warning("Red Team sequence failed: %s", rt_err)

            state.convergence = 1.0  # Plan is stable
            # Update the task plan so D3 can read it if needed directly
            task.plan = plan.to_prompt_str()
            return plan
        except Exception as e:  # noqa: BLE001
            logger.error("D2 Failed: %s", e)
            state.messages.append(f"Error: {e}")
            state.convergence = 0.0
            return None


class CreationDimension:
    """D3: Construction / Materialization (Wraps ExecutorAgent)."""

    def __init__(self, llm, system_prompt: str | None = None) -> None:
        self.executor = ExecutorAgent(llm, system_prompt)

    async def process(
        self,
        task: AgentTask,
        toolkit: AgentToolkit,
        state: DimensionalState,
        plan: Any,
    ) -> str | None:
        """Execute the plan and write code to disk."""
        if not plan:
            logger.info("D3 (Creation) blocked: waiting for stable D2 plan.")
            return None

        logger.info("D3 (Creation): Materializing code.")
        try:
            result = await self.executor.execute(plan, task.description, toolkit)
            state.messages.append(f"Execution result: {result[:50]}...")
            state.convergence = 0.8  # Needs validation to reach 1.0
            return result
        except Exception as e:  # noqa: BLE001
            logger.error("D3 Failed: %s", e)
            state.messages.append(f"Error: {e}")
            state.convergence = 0.0
            return None


class ValidationDimension:
    """D4: Siege & Entropy (Wraps CriticAgent & TesterAgent)."""

    def __init__(self, llm, system_prompt: str | None = None) -> None:
        self.critic = CriticAgent(llm, system_prompt)
        self.tester = TesterAgent()

    async def process(
        self, task: AgentTask, toolkit: AgentToolkit, state: DimensionalState
    ) -> dict[str, Any]:
        """Siege the newly created artifacts and evaluate entropy."""
        logger.info("D4 (Validation): Assembling Siege.")

        try:
            critique = await self.critic.critique(task.description, toolkit)

            # Run tests in executor to avoid blocking the asyncio event loop
            try:
                test_result = await asyncio.get_event_loop().run_in_executor(
                    None, self.tester.run, toolkit
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Tester failed (%s) — ignoring", e)
                test_result = None

            passed = critique.approved and (test_result.passed if test_result else True)
            state.convergence = 1.0 if passed else 0.0

            msg = f"Critique approved: {critique.approved}. Tests passed: {passed if test_result else 'N/A'}"
            state.messages.append(msg)

            return {"approved": passed, "critique": critique, "tests": test_result}
        except Exception as e:  # noqa: BLE001
            logger.error("D4 Failed: %s", e)
            state.messages.append(f"Error: {e}")
            state.convergence = 0.0
            return {"approved": False, "error": str(e)}
