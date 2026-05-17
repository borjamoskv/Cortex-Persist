"""CORTEX Agent Runtime — Swarm Hierarchy (Planner + Re-exports).

The SwarmPlannerAgent lives here. Specialist bases and squad agents
have been extracted to ``specialist.py`` and ``squads.py`` respectively.
This module re-exports everything for backward compatibility.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from cortex.agents.base import BaseAgent
from cortex.agents.message_schema import AgentMessage, MessageKind
from cortex.extensions.llm.router import IntentProfile, route_request

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

from cortex.engine.war_council import WarCouncil

# Re-export specialist bases
from cortex.agents.specialist import (  # noqa: F401
    DatabaseSpecialistAgent,
    FormatSpecialistAgent,
    IntentSpecialistAgent,
    SpecialistAgent,
)

# Re-export squad agents
from cortex.agents.squads import (  # noqa: F401
    AestheticUIAgent,
    ByzantineAuditorAgent,
    CodeReviewerAgent,
    EntropyShieldAgent,
    ExploitCrafterAgent,
    ForensicTracerAgent,
    FormatAgent,
    FormalVerifierAgent,
    GithubReconAgent,
    IntentClassifierAgent,
    JITCompilerAgent,
    LifecycleSupervisorAgent,
    MarkdownSynthesizerAgent,
    QueryAgent,
    ReentrancyHunterAgent,
    RefactorAgent,
    SmartContractAuditorAgent,
    SocialGraphAnalyzerAgent,
    SovereignPlanner,
    TelemetryAnalystAgent,
    WebScraperScoutAgent,
)

logger = logging.getLogger("cortex.agents.swarm_hierarchy")


class SwarmPlannerAgent(BaseAgent):
    """Sovereign Planner Agent.

    Uses a powerful model to define strategy and orchestrate
    specialized agents for execution using a state-machine (Saga pattern).
    """

    def __init__(
        self,
        *args: Any,
        engine: CortexEngine | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.engine = engine
        self.sessions: dict[str, dict[str, Any]] = {}
        self.watchdog_interval = 5.0
        self._watchdog_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the agent and its background tasks."""
        await super().start()
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())
        logger.info(
            "[%s] SwarmPlannerAgent started with watchdog (Ω₄)",
            self.agent_id,
        )

    async def stop(self) -> None:
        """Stop the agent and cleanup."""
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
        await super().stop()
        logger.info("[%s] SwarmPlannerAgent stopped", self.agent_id)

    async def _watchdog_loop(self) -> None:
        """Background loop to monitor session timeouts (Ω₃)."""
        while True:
            try:
                await asyncio.sleep(self.watchdog_interval)
                now = asyncio.get_event_loop().time()
                expired = [
                    cid
                    for cid, s in self.sessions.items()
                    if s["status"] == "EXECUTING" and now > s["deadline"]
                ]
                for cid in expired:
                    logger.warning(
                        "[%s] Session %s timed out.",
                        self.agent_id,
                        cid,
                    )
                    await self._handle_timeout(cid)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[%s] Watchdog error: %s", self.agent_id, e)

    async def _persist_session(self, correlation_id: str) -> None:
        """Persist session state to the engine (Ω₂)."""
        if not self.engine or correlation_id not in self.sessions:
            return
        session = self.sessions[correlation_id]
        await self.engine.store(
            project="swarm_orchestration",
            content=json.dumps(session),
            fact_type="swarm_session",
            meta={
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
            },
            source=f"agent:{self.agent_id}",
        )

    async def handle_message(self, message: AgentMessage) -> None:
        """Handle incoming task requests and results."""
        if message.kind == MessageKind.TASK_REQUEST:
            await self._handle_new_task(message)
        elif message.kind == MessageKind.TASK_RESULT:
            await self._handle_task_result(message)

    async def _handle_new_task(self, message: AgentMessage) -> None:
        """Initialize a new swarm session and start the first step."""
        user_input = message.payload.get("input", "")
        correlation_id = message.correlation_id or "auto"

        logger.info(
            "[%s] Planning strategy for: %s",
            self.agent_id,
            user_input[:50],
        )

        # 1. Define Strategy
        strategy_json = await self._define_strategy_structured(user_input)

        # 2. War Council BFT Audit (Ω₁)
        council = WarCouncil()
        is_safe = await council.evaluate_strategy(
            planner_id=self.agent_id,
            strategy=strategy_json,
            bus=self.bus,
        )

        if not is_safe:
            await self.send_result(
                recipient=message.sender,
                result={
                    "status": "REJECTED",
                    "reason": ("War Council detected potential hallucination or unsafe strategy."),
                },
                correlation_id=correlation_id,
            )
            return

        # 3. Initialize Session State
        now = asyncio.get_event_loop().time()
        timeout = strategy_json.get("TIMEOUT", 30.0)
        tasks = strategy_json.get("TASKS", [])
        task_states = {t["id"]: "PENDING" for t in tasks}

        self.sessions[correlation_id] = {
            "originator": message.sender,
            "input": user_input,
            "strategy": strategy_json,
            "tasks": tasks,
            "task_states": task_states,
            "results": {},
            "status": "EXECUTING",
            "created_at": now,
            "deadline": now + timeout,
            "retries": {},
        }

        await self._persist_session(correlation_id)

        await self._notify(
            intent="PLANNING_INITIATED",
            payload={
                "correlation_id": correlation_id,
                "model": "Gemini 1.5 Pro",
                "input_tokens": len(user_input),
            },
        )

        await self._dispatch_ready_tasks(correlation_id)

    async def _handle_task_result(self, message: AgentMessage) -> None:
        """Process result from a specialist and trigger next tasks."""
        correlation_id = message.correlation_id
        if correlation_id not in self.sessions:
            logger.warning(
                "[%s] Result for unknown session: %s",
                self.agent_id,
                correlation_id,
            )
            return

        session = self.sessions[correlation_id]
        specialist_id = message.sender
        result_data = message.payload.get("result", {})

        task_info = next(
            (
                t
                for t in session["tasks"]
                if t.get("agent") == specialist_id
                and session["task_states"].get(t["id"]) == "EXECUTING"
            ),
            None,
        )

        if not task_info:
            logger.warning(
                "[%s] No matching EXECUTING task for %s",
                self.agent_id,
                specialist_id,
            )
            return

        task_id = task_info["id"]
        logger.info(
            "[%s] Task %s completed by %s",
            self.agent_id,
            task_id,
            specialist_id,
        )

        await self._notify(
            intent="TASK_COMPLETED",
            payload={
                "correlation_id": correlation_id,
                "task_id": task_id,
                "agent": specialist_id,
                "status": result_data.get("status", "UNKNOWN"),
            },
        )

        if result_data.get("status") == "FAIL":
            session["task_states"][task_id] = "FAILED"
            await self._handle_task_failure(correlation_id, task_id, result_data)
            return
        elif result_data.get("status") == "REINCARNATED":
            logger.warning(
                "[%s] Agent %s reincarnated. Resuming task %s.",
                self.agent_id,
                specialist_id,
                task_id,
            )
            session["task_states"][task_id] = "PENDING"
            await self._dispatch_ready_tasks(correlation_id)
            return

        session["results"][task_id] = result_data
        session["task_states"][task_id] = "COMPLETED"

        await self._persist_session(correlation_id)

        if all(s == "COMPLETED" for s in session["task_states"].values()):
            await self._finalize_session(correlation_id)
        else:
            await self._dispatch_ready_tasks(correlation_id)

    async def _dispatch_ready_tasks(self, correlation_id: str) -> None:
        """Identify and dispatch tasks whose dependencies are met."""
        session = self.sessions[correlation_id]

        ready_tasks = []
        for task in session["tasks"]:
            tid = task["id"]
            if session["task_states"][tid] != "PENDING":
                continue
            deps = task.get("dependencies", [])
            if all(session["task_states"].get(d) == "COMPLETED" for d in deps):
                ready_tasks.append(task)

        if not ready_tasks:
            return

        logger.info(
            "[%s] Dispatching %d ready tasks in session %s",
            self.agent_id,
            len(ready_tasks),
            correlation_id,
        )

        dispatch_coros = []
        for task_info in ready_tasks:
            tid = task_info["id"]
            specialist = task_info.get("agent")
            task_desc = task_info.get("task")
            session["task_states"][tid] = "EXECUTING"
            dispatch_coros.append(
                self.request_task(
                    recipient=specialist,
                    task_payload={
                        "input": session["input"],
                        "task": task_desc,
                        "context": session["results"],
                    },
                    correlation_id=correlation_id,
                )
            )

        await asyncio.gather(*dispatch_coros)

    async def _handle_task_failure(
        self,
        correlation_id: str,
        task_id: str,
        error_data: dict[str, Any],
    ) -> None:
        """Handle failure in a DAG task (Ω₄)."""
        session = self.sessions[correlation_id]
        retries = session["retries"].get(task_id, 0)
        max_retries = session["strategy"].get("MAX_RETRIES", 2)

        if retries < max_retries:
            session["retries"][task_id] = retries + 1
            logger.info(
                "[%s] Retrying task %s (%d/%d)",
                self.agent_id,
                task_id,
                retries + 1,
                max_retries,
            )
            task_info = next(
                (t for t in session["tasks"] if t["id"] == task_id),
                None,
            )
            if task_info:
                session["task_states"][task_id] = "EXECUTING"
                await self._persist_session(correlation_id)
                await self.request_task(
                    recipient=task_info["agent"],
                    task_payload={
                        "input": session["input"],
                        "task": task_info.get("task"),
                        "context": session["results"],
                    },
                    correlation_id=correlation_id,
                )
                return

        error_msg = error_data.get("error", "Unknown error")
        await self._abort_session(
            correlation_id,
            f"Task {task_id} failed after retries: {error_msg}",
        )

    async def _handle_timeout(self, correlation_id: str) -> None:
        """Handle session timeout."""
        await self._abort_session(correlation_id, "Session timeout reached (SAGA-ABORT)")

    async def _abort_session(self, correlation_id: str, reason: str) -> None:
        """Abort session and notify originator (Ω₉)."""
        session = self.sessions.pop(correlation_id)
        session["status"] = "ABORTED"
        session["error"] = reason

        logger.error(
            "[%s] Aborting session %s: %s",
            self.agent_id,
            correlation_id,
            reason,
        )

        await self._persist_session_state(correlation_id, session)

        await self.send_result(
            recipient=session["originator"],
            result={"status": "FAILED", "reason": reason},
            correlation_id=correlation_id,
        )

    async def _persist_session_state(self, correlation_id: str, session: dict[str, Any]) -> None:
        """Persist a session dict that might have been popped."""
        if not self.engine:
            return
        await self.engine.store(
            project="swarm_orchestration",
            content=json.dumps(session),
            fact_type="swarm_session",
            meta={
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
                "status": session["status"],
            },
            source=f"agent:{self.agent_id}",
        )

    async def _finalize_session(self, correlation_id: str) -> None:
        """Synthesize final results and respond to originator."""
        session = self.sessions.pop(correlation_id)

        logger.info(
            "[%s] Finalizing session %s",
            self.agent_id,
            correlation_id,
        )

        final_report = await self._synthesize_final_report(session)

        await self.send_result(
            recipient=session["originator"],
            result={
                "status": "COMPLETED",
                "final_report": final_report,
                "steps_executed": len(session["results"]),
            },
            correlation_id=correlation_id,
        )

    async def _define_strategy_structured(self, user_input: str) -> dict[str, Any]:
        """Invoke powerful model to synthesize a DAG strategy."""
        res = await route_request(
            prompt=(
                "DEVELOP SOVEREIGN DAG STRATEGY (Ω₂). JSON ONLY.\n"
                f"INPUT: {user_input}\n"
                "DEFINE A GRAPH OF SPECIALISTS "
                "(intent_classifier, query_agent, format_agent).\n"
                "Tasks execute in parallel when possible. "
                "Use 'dependencies' to define flow.\n"
                'JSON: {"OBJECTIVE": string, '
                '"TASKS": [{"id": "T1", "agent": "...", '
                '"task": "...", "dependencies": []}], '
                '"MAX_RETRIES": int, "TIMEOUT": float}'
            ),
            intent=IntentProfile.PLANNER,
        )
        try:
            content = res.get("content", "{}")
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception:
            return {
                "OBJECTIVE": "Fallback execution",
                "TASKS": [
                    {
                        "id": "T1",
                        "agent": "intent_classifier",
                        "task": "analyze intent",
                        "dependencies": [],
                    },
                    {
                        "id": "T2",
                        "agent": "format_agent",
                        "task": "polish output",
                        "dependencies": ["T1"],
                    },
                ],
                "MAX_RETRIES": 2,
                "TIMEOUT": 30.0,
            }

    async def _synthesize_final_report(self, session: dict[str, Any]) -> str:
        """Final L1 synthesis of all specialist outputs."""
        res = await route_request(
            prompt=(
                "SYNTHESIZE FINAL SOVEREIGN REPORT (Ω₅).\n"
                f"ORIGINAL INPUT: {session['input']}\n"
                f"SPECIALIST RESULTS: {json.dumps(session['results'])}\n"
                "Emita un reporte ejecutivo Industrial Noir."
            ),
            intent=IntentProfile.PLANNER,
        )
        return res.get("content", "Synthesis failed.")

    async def _audit_strategy(self, strategy: str) -> str:
        """Self-Correction loop (Ω₁)."""
        res = await route_request(
            prompt=(
                "AUDIT STRATEGY FOR BYZANTINE FAULT TOLERANCE:\n"
                f"{strategy}\n\nEmit PASS or FAIL with reason."
            ),
            intent=IntentProfile.SPECIALIST,
        )
        return res.get("content", "Audit failed.")

    async def _notify(self, intent: str, payload: dict[str, Any]) -> None:
        """Sovereign Notification Protocol (Ω₅)."""
        logger.info("[NOTIFY:%s] %s", intent, json.dumps(payload))

        if self.engine:
            await self.engine.store(
                project="swarm_notifications",
                content=json.dumps(payload),
                fact_type="notification",
                meta={"intent": intent, "agent_id": self.agent_id},
                source=f"agent:{self.agent_id}",
            )

        try:
            from cortex.nexus_v8 import (
                DomainOrigin,
                IntentType,
                NexusWorldModel,
                Priority,
                WorldMutation,
            )

            if hasattr(self, "nexus") and isinstance(self.nexus, NexusWorldModel):
                await self.nexus.mutate(
                    WorldMutation(
                        origin=DomainOrigin.CORTEX_CORE,
                        intent=getattr(IntentType, intent, intent),
                        project="swarm",
                        priority=Priority.NORMAL,
                        payload=payload,
                    )
                )
        except ImportError:
            pass
        except Exception as e:
            logger.debug("Nexus notification skipped: %s", e)
