"""MOSKV-1 — Tesseract Core Manifold.

The main orchestrator loop simulating 4D cognitive wave collapse.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from cortex.aether.models import AgentTask, TaskStatus
from cortex.aether.tools import AgentToolkit
from cortex.manifold.convergence import ConvergenceEngine
from cortex.manifold.dimensions import (
    CreationDimension,
    DecisionDimension,
    PerceptionDimension,
    ValidationDimension,
)
from cortex.manifold.models import DimensionType, WaveState

logger = logging.getLogger("cortex.manifold.core")


class TesseractManifold:
    """The 4D Cognitive Manifold engine."""

    def __init__(self, llm_provider: str = "qwen", agent_id: str | None = None) -> None:
        from cortex.agents.registry import AgentRegistry
        from cortex.llm.provider import LLMProvider

        self._llm = LLMProvider(provider=llm_provider)

        system_prompt = None
        if agent_id:
            registry = AgentRegistry()
            registry.load_all()
            if agent_def := registry.get(agent_id):
                system_prompt = agent_def.system_prompt

        self.d1 = PerceptionDimension()
        self.d2 = DecisionDimension(self._llm, system_prompt)
        self.d3 = CreationDimension(self._llm, system_prompt)
        self.d4 = ValidationDimension(self._llm, system_prompt)
        self.max_cycles = 5

    async def run(self, task: AgentTask, toolkit: AgentToolkit) -> AgentTask:
        """Run the manifold wave collapse for a given task."""
        state = WaveState()
        logger.info("◈ TESSERACT IGNITION — Task [%s] %s", task.id, task.title)

        branch = f"tesseract/{task.id}"
        toolkit.git_create_branch(branch)
        task.branch = branch

        # Wave iterations
        for cycle in range(1, self.max_cycles + 1):
            state.cycle = cycle
            logger.info("══ CICLO %d ════════════════════════════", cycle)
            task.status = f"Tesseract Cycle {cycle}"

            # Run active dimensions concurrently
            # D1: Perception (Context, History, Predix)
            async def run_d1() -> dict | None:
                if state.dimensions[DimensionType.D1_PERCEPTION].active:
                    return await self.d1.process(
                        task, toolkit, state.dimensions[DimensionType.D1_PERCEPTION]
                    )
                return None

            # D2: Decision (Plan, Intent expansion)
            async def run_d2() -> object | None:
                if state.dimensions[DimensionType.D2_DECISION].active:
                    return await self.d2.process(
                        task, toolkit, state.dimensions[DimensionType.D2_DECISION]
                    )
                return None

            # Gather D1 and D2 first so D3 has the new plan structure if mutated
            d1_res, d2_res = await asyncio.gather(run_d1(), run_d2())
            state.dimensions[DimensionType.D1_PERCEPTION].output = d1_res
            state.dimensions[DimensionType.D2_DECISION].output = d2_res

            # D3: Creation (Materialization, Scaffold, Code)
            async def run_d3(plan: object | None) -> str | None:
                if state.dimensions[DimensionType.D3_CREATION].active:
                    return await self.d3.process(
                        task,
                        toolkit,
                        state.dimensions[DimensionType.D3_CREATION],
                        plan,
                    )
                return None

            # D4: Validation (Siege, Fitness, Entropy reduction)
            async def run_d4() -> dict | None:
                if state.dimensions[DimensionType.D4_VALIDATION].active:
                    return await self.d4.process(
                        task, toolkit, state.dimensions[DimensionType.D4_VALIDATION]
                    )
                return None

            # Gather D3 and D4
            d3_res, d4_res = await asyncio.gather(run_d3(d2_res), run_d4())
            state.dimensions[DimensionType.D3_CREATION].output = d3_res
            state.dimensions[DimensionType.D4_VALIDATION].output = d4_res

            # Calculate metrics from node outputs
            valid = False
            if d4_res and isinstance(d4_res, dict):
                valid = d4_res.get("approved", False)

            # Map the reality to the wave metrics
            state.metrics.siege_survival_rate = 1.0 if valid else 0.5
            state.metrics.entropy_delta = -1.0 if valid else 1.0
            state.metrics.prediction_accuracy = 0.8  # Stub for real D1 tracking
            state.metrics.fitness_score = 0.9 if valid else 0.6
            state.metrics.intent_drift = 0.05

            if ConvergenceEngine.evaluate(state):
                logger.info("◈ CONVERGENCIA ALCANZADA EN %d CICLOS", cycle)
                break
            else:
                amps = ConvergenceEngine.calculate_amplification(state)
                logger.info(
                    "Divergencia detectada. Amplificando: %s",
                    [a.value for a in amps],
                )

                # If D4 found issues, inject them back into D2/D3 reality for next loop
                if d4_res and not d4_res.get("approved"):
                    issues = []
                    critique = d4_res.get("critique")
                    if critique:
                        issues = getattr(critique, "issues", [])
                    if issues:
                        task.description += "\n\nSIEGE FEEDBACK:\n- " + "\n- ".join(issues)

        else:
            logger.warning(
                "◈ CONVERGENCIA PARCIAL / FORZADA (Límite %d ciclos)",
                self.max_cycles,
            )
            self._persist_ghost(task, "Tesseract forced convergence limit reached.")

        # Final commit and crystallization
        diff = toolkit.git_diff()
        if diff.strip() and not diff.startswith("[ERROR]"):
            toolkit.git_commit(f"tesseract({task.id}): {task.title[:60]}")

        task.status = TaskStatus.DONE
        d3_out = state.dimensions[DimensionType.D3_CREATION].output
        task.result = str(d3_out) if d3_out else "Converged with no material changes."

        self._persist_decision(task, task.result)
        self._notify(f"Tesseract ◈ [{task.id}]", task.title)

        await self._llm.close()
        return task

    def run_sync(self, task: AgentTask, toolkit: AgentToolkit) -> AgentTask:
        """Synchronous wrapper for tests or CLI entrypoints."""
        return asyncio.run(self.run(task, toolkit))

    def _persist_decision(self, task: AgentTask, result: str) -> None:
        """Persist completion decision to CORTEX."""
        try:
            import subprocess

            msg = f"Tesseract converged task [{task.id}]: {task.title}. Branch: {task.branch}. Result: {result[:200]}"
            subprocess.run(
                [
                    "python",
                    "-m",
                    "cortex.cli",
                    "store",
                    "--type",
                    "decision",
                    "--source",
                    "agent:tesseract",
                    "CORTEX",
                    msg,
                ],
                cwd=str(Path.home() / "cortex"),
                capture_output=True,
                timeout=10,
            )
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("CORTEX persist failed: %s", e)

    def _persist_ghost(self, task: AgentTask, reason: str) -> None:
        """Persist incomplete convergence as a ghost."""
        try:
            import subprocess

            msg = f"Tesseract partial convergence [{task.id}]: {task.title}. Reason: {reason}"
            subprocess.run(
                [
                    "python",
                    "-m",
                    "cortex.cli",
                    "store",
                    "--type",
                    "ghost",
                    "--source",
                    "agent:tesseract",
                    "CORTEX",
                    msg,
                ],
                cwd=str(Path.home() / "cortex"),
                capture_output=True,
                timeout=10,
            )
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("CORTEX ghost persist failed: %s", e)

    @staticmethod
    def _notify(title: str, body: str) -> None:
        """macOS notification via osascript."""
        try:
            import subprocess

            script = f'display notification "{body[:200]}" with title "{title}"'
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
        except (subprocess.SubprocessError, OSError):
            pass
