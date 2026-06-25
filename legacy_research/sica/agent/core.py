# [C5-REAL] Exergy-Maximized
"""SICA Agent - The Integrated Self-Improving Cognitive Architecture.

Integrates the three SICA layers into a single agent that inherits
from CORTEX BaseAgent:

  ┌─────────────────────────────────────────┐
  │            META-LEVEL                    │
  │  Constitution + MetaLevel                │
  │  "Was my strategy correct?"              │
  │         MONITORS ↑   ↓ CONTROLS          │
  │  ┌──────────────────────────────────┐    │
  │  │         OBJECT-LEVEL             │    │
  │  │  SearchStrategy + ObjectLevel    │    │
  │  │  plan → tools → result           │    │
  │  └──────────────────────────────────┘    │
  └─────────────────────────────────────────┘

The SICAAgent lifecycle per task:
  1. Receive task (handle_message)
  2. Object-level begins execution trace
  3. Object-level executes steps guided by current strategy
  4. Object-level finalizes trace
  5. Meta-level MONITORS the trace → produces MetaJudgment
  6. Meta-level CONTROLS the strategy → applies mutations
  7. Constitutional evaluation gates the output
  8. Result emitted (or revised/aborted)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from legacy_research.agents.base import BaseAgent
from legacy_research.agents.manifest import AgentManifest
from legacy_research.agents.message_schema import AgentMessage, MessageKind
from legacy_research.agents.tools import ToolRegistry
from legacy_research.sica.agent.assessment import SelfAssessor
from legacy_research.sica.agent.emission import AgentEmitter
from legacy_research.sica.agent.stats import _LifetimeStats
from legacy_research.sica.autonomy import (
    AdaptiveRetry,
    AutonomousTick,
    SpeculativeFork,
)
from legacy_research.sica.constitution import Constitution
from legacy_research.sica.meta_level import MetaAction, MetaJudgment, MetaLevel
from legacy_research.sica.object_level import ExecutionTrace, ObjectLevel, StepOutcome
from legacy_research.sica.persistence import load_or_default, save_genome
from legacy_research.sica.strategy import SearchStrategy

logger = logging.getLogger("cortex.sica.agent")


class SICAAgent(BaseAgent):
    """Self-Improving Cognitive Architecture Agent.

    A CORTEX agent that monitors its own reasoning process and
    evolves its search strategy across task executions.

    The agent distinguishes between:
      - Object-level failures: "the task failed" → retry/fix
      - Meta-level failures: "my thinking was wrong" → mutate strategy

    This implements Nelson-Narens (1990) metacognitive architecture
    with Anthropic Constitutional AI output gating.
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,
        tool_registry: ToolRegistry | None = None,
        constitution: Constitution | None = None,
        strategy: SearchStrategy | None = None,
        max_retries_per_task: int = 3,
        persist_dir: Path | str | None = None,
        enable_autonomy: bool = True,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)

        # ── Strategy: resume from persisted genome or start fresh ──
        if strategy is not None:
            self._strategy = strategy
        else:
            self._strategy = load_or_default(
                manifest.agent_id,
                directory=persist_dir,
            )

        self._persist_dir = persist_dir
        self._object_level = ObjectLevel(self._strategy)
        self._meta_level = MetaLevel(self._strategy, constitution)
        self._max_retries = max_retries_per_task
        self._task_counter = 0

        # Sub-components
        self._lifetime_stats = _LifetimeStats()
        self._assessor = SelfAssessor(self._object_level, self._strategy)
        self._emitter = AgentEmitter(self, self._lifetime_stats)

        # ── Autonomy primitives ──────────────────────────────────
        self._autonomy_enabled = enable_autonomy
        self._speculative_fork = SpeculativeFork(n_forks=3)
        self._adaptive_retry = AdaptiveRetry(base_budget=max_retries_per_task)
        self._autonomous_tick = AutonomousTick(min_interval_s=60.0)

    @property
    def strategy(self) -> SearchStrategy:
        return self._strategy

    @property
    def meta_level(self) -> MetaLevel:
        return self._meta_level

    @property
    def object_level(self) -> ObjectLevel:
        return self._object_level

    # ── BaseAgent Implementation ─────────────────────────────────

    async def handle_message(self, message: AgentMessage) -> None:
        """Process an incoming message through the SICA loop."""
        if message.kind == MessageKind.TASK_REQUEST:
            await self._execute_task(message)
        elif message.kind == MessageKind.HEARTBEAT:
            await self.emit_heartbeat()
        else:
            logger.debug("[%s] Ignoring message kind=%s", self.agent_id, message.kind)

    async def on_start(self) -> None:
        logger.info(
            "[%s] SICA Agent started (genome gen=%d, hash=%s, autonomy=%s)",
            self.agent_id,
            self._strategy.genome.generation,
            self._strategy.genome.genome_hash,
            self._autonomy_enabled,
        )

    async def on_stop(self) -> None:
        # Persist genome on shutdown - learned strategies survive restarts
        try:
            save_genome(
                self._strategy.genome,
                agent_id=self.agent_id,
                directory=self._persist_dir,
            )
        except Exception as exc:
            logger.error("[%s] Failed to persist genome: %s", self.agent_id, exc)

        logger.info(
            "[%s] SICA Agent stopped. Lifetime: %s",
            self.agent_id,
            self._lifetime_stats.summary(),
        )

    async def tick(self) -> None:
        """Autonomous self-diagnostic tick (runs during idle).

        This is the agent's inner monologue - proactive reflection
        without external stimulus. Nelson-Narens without a trigger.
        """
        if not self._autonomy_enabled:
            return
        if not self._autonomous_tick.should_tick():
            return

        report = self._autonomous_tick.execute(
            self._strategy,
            self._object_level,
            self._meta_level,
        )

        if report["actions"]:
            logger.info(
                "[%s] Autonomous tick #%d: %s",
                self.agent_id,
                self._autonomous_tick.tick_count,
                report["actions"],
            )

            # Auto-save after autonomous modifications
            try:
                save_genome(
                    self._strategy.genome,
                    agent_id=self.agent_id,
                    directory=self._persist_dir,
                )
            except Exception as exc:
                logger.error("[%s] Auto-save failed: %s", self.agent_id, exc)

    # ── Core SICA Loop ───────────────────────────────────────────

    async def _execute_task(self, message: AgentMessage) -> None:
        """Execute a task through the full SICA metacognitive loop."""
        self._task_counter += 1
        task_id = message.payload.get("task_id", f"sica-{self._task_counter}")
        objective = message.payload.get("objective", "")
        task_input = message.payload.get("input", {})

        logger.info("[%s] SICA task %s: %s", self.agent_id, task_id, objective[:100])

        retry_count = 0
        max_retries = self._max_retries
        last_judgment: MetaJudgment | None = None

        while retry_count <= max_retries:
            trace, result, outcome, confidence = await self._run_phase_1_object_level(
                task_id, objective, task_input
            )

            judgment = self._run_phase_2_monitor(trace)
            last_judgment = judgment

            max_retries = self._run_phase_3_control(judgment, max_retries)

            if judgment.constitutional_verdict and judgment.constitutional_verdict.abort_needed:
                await self._emitter.emit_abort(message, task_id, judgment)
                return

            if outcome == StepOutcome.SUCCESS:
                await self._handle_success(message, task_id, result, judgment)
                return

            retry_count, should_continue = self._handle_failure_retry(
                judgment, retry_count, max_retries
            )
            if should_continue:
                continue
            break

        logger.error("[%s] Task %s exhausted %d retries", self.agent_id, task_id, max_retries)

        if last_judgment and MetaAction.ESCALATE_TO_HUMAN in last_judgment.recommended_actions:
            await self._emitter.emit_escalation(message, task_id, last_judgment)
        else:
            await self._emitter.emit_failure(message, task_id, last_judgment)

    async def _run_phase_1_object_level(
        self, task_id: str, objective: str, task_input: dict[str, Any]
    ):
        trace = self._object_level.begin_task(task_id, objective)
        try:
            result = await self._run_object_level(task_input, objective)
            outcome = StepOutcome.SUCCESS
        except Exception as exc:
            self._object_level.record_step(
                action="task_execution", outcome=StepOutcome.FAILURE, error=repr(exc)
            )
            result = {"error": repr(exc)}
            outcome = StepOutcome.FAILURE

        self._assessor._strategy = self._strategy
        confidence = self._assessor.assess_confidence(outcome)
        trace = self._object_level.end_task(outcome, confidence=confidence)
        return trace, result, outcome, confidence

    def _run_phase_2_monitor(self, trace: ExecutionTrace) -> MetaJudgment:
        judgment = self._meta_level.monitor(trace)
        self._lifetime_stats.record_judgment(judgment)
        logger.info(
            "[%s] Meta-judgment: class=%s meta_failure=%s confidence=%.2f",
            self.agent_id,
            judgment.failure_class.value if judgment.failure_class else "none",
            judgment.is_meta_failure,
            judgment.confidence,
        )
        return judgment

    def _run_phase_3_control(self, judgment: MetaJudgment, max_retries: int) -> int:
        if judgment.requires_strategy_mutation:
            mutations = self._meta_level.control(judgment)
            self._lifetime_stats.mutations += len(mutations)

            if (
                self._autonomy_enabled
                and judgment.is_meta_failure
                and len(self._object_level.trace_archive) >= 3
            ):
                self._strategy = self._speculative_fork.speculate(
                    self._strategy, judgment, self._object_level.trace_archive[-5:]
                )
                self._object_level.strategy = self._strategy
                self._meta_level._strategy = self._strategy

            logger.info(
                "[%s] Applied %d strategy mutations (gen=%d)",
                self.agent_id,
                len(mutations),
                self._strategy.genome.generation,
            )

        if self._autonomy_enabled:
            return self._adaptive_retry.compute_budget(judgment)
        return max_retries

    async def _handle_success(
        self, message: AgentMessage, task_id: str, result: dict[str, Any], judgment: MetaJudgment
    ) -> None:
        if judgment.constitutional_verdict and judgment.constitutional_verdict.revision_needed:
            logger.warning("[%s] Output requires constitutional revision", self.agent_id)
            result = self._assessor.revise_output(result, judgment)
        await self._emitter.emit_result(message, task_id, result, judgment)

    def _handle_failure_retry(
        self, judgment: MetaJudgment, retry_count: int, max_retries: int
    ) -> tuple[int, bool]:
        retry_count += 1
        if judgment.is_meta_failure:
            logger.info(
                "[%s] Meta-failure detected. Retrying with mutated strategy "
                "(attempt %d/%d, genome=%s)",
                self.agent_id,
                retry_count,
                max_retries,
                self._strategy.genome.genome_hash,
            )
            return retry_count, True
        if retry_count <= max_retries:
            logger.info(
                "[%s] Object-level failure. Simple retry (%d/%d)",
                self.agent_id,
                retry_count,
                max_retries,
            )
            return retry_count, True
        return retry_count, False

    async def _run_object_level(
        self,
        task_input: dict[str, Any],
        objective: str,
    ) -> dict[str, Any]:
        """Execute the actual task using available tools.

        This is where subclasses plug in domain-specific logic.
        The base implementation provides a strategy-guided execution skeleton.
        """
        genome = self._strategy.genome

        # Step 1: Decomposition check
        difficulty = task_input.get("difficulty", 0.5)
        if self._object_level.should_decompose(difficulty):
            self._object_level.record_step(
                action="decompose",
                outcome=StepOutcome.SUCCESS,
                heuristic_applied="decompose_first",
                output_summary=f"Decomposing task (depth={genome.decomposition_depth})",
            )

        # Step 2: Tool selection (guided by strategy)
        for tool_name in genome.tool_priority[:3]:  # Try top-3 tools
            start = time.monotonic()
            try:
                if self.tools.has(tool_name):
                    result = await self.use_tool(tool_name, objective=objective, **task_input)
                    duration = (time.monotonic() - start) * 1000

                    self._object_level.record_step(
                        action=f"use_tool:{tool_name}",
                        outcome=StepOutcome.SUCCESS,
                        tool_used=tool_name,
                        duration_ms=duration,
                        output_summary=str(result)[:200] if result else "",
                    )
                    return {"tool": tool_name, "result": result}
                self._object_level.record_step(
                    action=f"tool_lookup:{tool_name}",
                    outcome=StepOutcome.SKIPPED,
                    tool_used=tool_name,
                    output_summary=f"Tool '{tool_name}' not available",
                )
            except Exception as exc:
                duration = (time.monotonic() - start) * 1000
                self._object_level.record_step(
                    action=f"use_tool:{tool_name}",
                    outcome=StepOutcome.FAILURE,
                    tool_used=tool_name,
                    error=repr(exc),
                    duration_ms=duration,
                )

                # Check escalation after each failure
                if self._object_level.should_escalate():
                    raise RuntimeError(
                        f"Escalation threshold reached after tool '{tool_name}' failure"
                    ) from exc

        # Step 3: Verification (if verify_before_emit heuristic is active)
        verify_h = None
        for h in genome.heuristics:
            if h.name == "verify_before_emit":
                verify_h = h
                break

        if verify_h and verify_h.weight > 0.5:
            self._object_level.record_step(
                action="verify",
                outcome=StepOutcome.SUCCESS,
                heuristic_applied="verify_before_emit",
                output_summary="Verification pass (no tools executed)",
            )

        return {
            "status": "completed",
            "note": "base execution - override _run_object_level for domain logic",
        }

    # ── Introspection API ────────────────────────────────────────

    def introspect(self) -> dict[str, Any]:
        """Full introspection of the SICA agent's cognitive state.

        Returns the complete meta-level report plus lifetime stats.
        """
        return {
            "agent_id": self.agent_id,
            "meta_level": self._meta_level.introspect(),
            "lifetime": self._lifetime_stats.to_dict(),
            "object_level": {
                "traces_archived": len(self._object_level.trace_archive),
                "last_trace": (
                    self._object_level.last_trace.to_dict()
                    if self._object_level.last_trace
                    else None
                ),
            },
        }
