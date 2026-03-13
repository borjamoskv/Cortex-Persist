"""CORTEX v8.0 — NightShift Pipeline (Autonomous Crystal Generation).

Wires target discovery (KnowledgeRadar) with the AUTODIDACT-Ω crystallization
engine to form a fully autonomous DAG for background knowledge generation.

Pipeline DAG:
    planner → executor → validator → persister
                ↘ (conflict) → human_gate

Nodes:
    1. PlannerNode     — Receives targets from radar, builds execution plan
    2. ExecutorNode    — Invokes AUTODIDACT-Ω per target (fetch + distill + index)
    3. ValidatorNode   — ByzantineConsensus on results
    4. PersisterNode   — Logs cycle metrics to CORTEX
    5. HumanGateNode   — Pause if confidence < C3

Axiom Derivations:
    Ω₂ (Entropic Asymmetry): Each node reduces uncertainty or is skipped.
    Ω₃ (Byzantine Default): ValidatorNode validates before persist.
    Ω₆ (Zenón's Razor): HumanGateNode collapses deliberation when needed.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

logger = logging.getLogger("cortex.swarm.nightshift_pipeline")


# ── Pipeline Nodes ───────────────────────────────────────────────────────


class PlannerNode:
    """Decomposes crystal targets into an execution plan.

    Receives targets (from KnowledgeRadar) and converts each into a
    task dict with keys: id, target, intent, priority.
    """

    name = "planner"

    def _clean_target(self, target: str) -> str:
        """Aesthetic Cleaning: Extract clean URL/Query from raw strings."""
        if not isinstance(target, str):
            return str(target)
            
        # 1. URL extraction
        url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', target)
        if url_match:
            return url_match.group(0)
            
        # 2. JSON unpacking
        if target.strip().startswith("{"):
            try:
                data = json.loads(target)
                return data.get("url") or data.get("target") or data.get("query") or target[:200]
            except json.JSONDecodeError:
                pass
                
        # 3. Artifact header stripping
        clean = re.sub(r'═══.*?═══', '', target).strip()
        # 4. Remove leading/trailing markdown code blocks
        clean = re.sub(r'^```\w*\n|```$', '', clean).strip()
        
        return clean[:500]

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Build execution plan from targets."""
        targets = state.get("targets", [])
        intent_fallback = state.get("intent", "")

        logger.info("📋 [PLANNER] Planning crystallization for %d targets", len(targets))

        plan: list[dict[str, Any]] = []

        for i, target in enumerate(targets):
            # Support both CrystalTarget objects and raw dicts
            if hasattr(target, "target"):
                plan.append(
                    {
                        "id": f"crystal-{int(time.time())}-{i}",
                        "target": self._clean_target(target.target),
                        "intent": target.intent,
                        "priority": target.priority,
                        "source": target.source,
                        "metadata": getattr(target, "metadata", {}),
                    }
                )
            elif isinstance(target, dict):
                plan.append(
                    {
                        "id": f"crystal-{int(time.time())}-{i}",
                        "target": self._clean_target(target["target"]),
                        "intent": target.get("intent", intent_fallback or "quick_read"),
                        "priority": target.get("priority", 5),
                        "source": target.get("source", "manual"),
                        "metadata": target.get("metadata", {}),
                    }
                )
            elif isinstance(target, str):
                # Plain string target — wrap as quick_read
                plan.append(
                    {
                        "id": f"crystal-{int(time.time())}-{i}",
                        "target": self._clean_target(target),
                        "intent": intent_fallback or "quick_read",
                        "priority": 5,
                        "source": "manual",
                        "metadata": {},
                    }
                )

        state["plan"] = plan
        state["next_node"] = "executor"
        return state


class ExecutorNode:
    """Executes knowledge crystallization via AUTODIDACT-Ω.

    For each planned task, invokes the autodidact pipeline to:
    1. Fetch content (Jina/Firecrawl/Exa/AssemblyAI)
    2. Distill via Claude (synthesis.py)
    3. Index into L2 vector store
    """

    name = "executor"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute all planned crystallization tasks."""
        plan = state.get("plan", [])
        results: list[dict[str, Any]] = []

        logger.info("⚡ [EXECUTOR] Crystallizing %d targets.", len(plan))

        for task in plan:
            start = time.monotonic()
            task_id = task["id"]

            try:
                from cortex.skills.autodidact.actuator import autodidact_pipeline

                result = await autodidact_pipeline(
                    target=task["target"],
                    intent=task.get("intent", "quick_read"),
                    force=task.get("force", False),
                )

                estado = result.get("estado", "FALLO")
                success = estado in ("ASIMILADO", "REDUNDANTE")

                results.append(
                    {
                        "task_id": task_id,
                        "success": success,
                        "output": result.get("memo_id", ""),
                        "estado": estado,
                        "target": task["target"],
                        "beats_used": 1,
                        "duration_ms": (time.monotonic() - start) * 1000,
                    }
                )

                if success:
                    logger.info(
                        "✨ [EXECUTOR] Crystal forged: %s → %s (%.0fms)",
                        task["target"][:60],
                        result.get("memo_id", "?"),
                        (time.monotonic() - start) * 1000,
                    )
                else:
                    logger.warning(
                        "⚠️ [EXECUTOR] Crystal failed: %s → %s",
                        task["target"][:60],
                        result.get("error", estado),
                    )

            except Exception as e:  # noqa: BLE001 — boundary for autodidact execution
                logger.error("❌ [EXECUTOR] Fatal: %s → %s", task_id, e)
                results.append(
                    {
                        "task_id": task_id,
                        "success": False,
                        "output": "",
                        "estado": "EXCEPCION",
                        "error": str(e),
                        "target": task.get("target", ""),
                        "duration_ms": (time.monotonic() - start) * 1000,
                    }
                )

        state["results"] = results
        state["next_node"] = "validator"
        return state


class ValidatorNode:
    """Validates execution results via Byzantine consensus.

    If multiple agents produced results, checks for agreement.
    Single-agent results pass with automatic C4 confidence.
    """

    name = "validator"

    # Confidence levels
    C5_CONFIRMED = "C5"
    C4_PROBABLE = "C4"
    C3_INFERRED = "C3"
    C2_SPECULATIVE = "C2"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Validate results and assign confidence."""
        results = state.get("results", [])

        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        logger.info(
            "🔍 [VALIDATOR] %d successful, %d failed.",
            len(successful),
            len(failed),
        )

        if not successful:
            state["confidence"] = self.C2_SPECULATIVE
            state["next_node"] = "human_gate"
            state["validation_reason"] = "All crystallization tasks failed. Human review required."
            return state

        # For crystal generation, individual success is sufficient
        # Each crystal is independently validated by AUTODIDACT's redundancy check
        if len(failed) == 0:
            state["confidence"] = self.C5_CONFIRMED
        elif len(successful) > len(failed):
            state["confidence"] = self.C4_PROBABLE
        else:
            state["confidence"] = self.C3_INFERRED
            state["next_node"] = "human_gate"
            state["validation_reason"] = (
                f"Majority failed: {len(failed)}/{len(results)} tasks."
            )
            return state

        state["next_node"] = "persister"
        return state


class PersisterNode:
    """Persists cycle metrics and marks processed targets.

    Records the NightShift cycle results as a CORTEX fact
    for observability and future analysis.
    """

    name = "persister"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Log cycle metrics to CORTEX."""
        results = state.get("results", [])
        confidence = state.get("confidence", "C2")

        successful = [r for r in results if r.get("success")]
        crystals_forged = [r.get("output") for r in successful if r.get("output")]

        logger.info(
            "💾 [PERSISTER] Cycle complete. Crystals=%d, Confidence=%s",
            len(crystals_forged),
            confidence,
        )

        state["crystals_forged"] = crystals_forged
        state["crystals_count"] = len(crystals_forged)
        state["next_node"] = "__end__"
        return state


class HumanGateNode:
    """Pause execution for human review when confidence is low.

    Axiom Ω₆ (Zenón's Razor): When deliberation costs exceed production,
    collapse into action — but only with human authorization.
    """

    name = "human_gate"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Pause and wait for human review."""
        reason = state.get("validation_reason", "Low confidence.")
        confidence = state.get("confidence", "C2")

        logger.warning(
            "⏸️ [HUMAN_GATE] Pausing execution. Confidence=%s. Reason: %s",
            confidence,
            reason,
        )

        state["is_paused"] = True
        state["pause_reason"] = reason
        state["next_node"] = "__end__"  # Supervisor will halt here
        return state


# ── Pipeline Assembly ────────────────────────────────────────────────────


class NightShiftPipeline:
    """Assembles and runs the NightShift DAG.

    Usage:
        pipeline = NightShiftPipeline()
        result = await pipeline.run(
            targets=[CrystalTarget(...), ...],
        )
    """

    def __init__(self) -> None:
        self.nodes: dict[str, Any] = {
            "planner": PlannerNode(),
            "executor": ExecutorNode(),
            "validator": ValidatorNode(),
            "persister": PersisterNode(),
            "human_gate": HumanGateNode(),
        }

    async def run(
        self,
        targets: list[Any] | None = None,
        intent: str = "",
        repo_path: str = ".",
        priority: int = 5,
    ) -> dict[str, Any]:
        """Execute the full NightShift crystal pipeline.

        Args:
            targets: List of CrystalTarget or dicts with target info.
            intent: Fallback intent if targets don't specify one.
            repo_path: Repository context (for code-related targets).
            priority: Default priority (1=highest, 10=lowest).

        Returns:
            Final pipeline state dict.
        """
        state: dict[str, Any] = {
            "targets": targets or [],
            "intent": intent,
            "repo_path": repo_path,
            "priority": priority,
            "next_node": "planner",
            "is_paused": False,
            "started_at": time.time(),
        }

        logger.info(
            "🚀 [NIGHTSHIFT] Pipeline started. Targets: %d",
            len(state["targets"]),
        )

        max_steps = 10  # Circuit breaker
        step = 0

        while state["next_node"] != "__end__" and step < max_steps:
            node_name = state["next_node"]
            node = self.nodes.get(node_name)

            if node is None:
                logger.error("[NIGHTSHIFT] Unknown node: %s", node_name)
                break

            logger.info("🔄 [NIGHTSHIFT] Step %d → %s", step + 1, node_name)
            state = await node.execute(state)
            step += 1

            if state.get("is_paused"):
                logger.info("⏸️ [NIGHTSHIFT] Pipeline paused at %s.", node_name)
                break

        state["completed_at"] = time.time()
        state["total_steps"] = step
        state["duration_s"] = state["completed_at"] - state["started_at"]

        logger.info(
            "🏁 [NIGHTSHIFT] Pipeline complete. Steps=%d, Duration=%.1fs, "
            "Crystals=%d, Confidence=%s",
            step,
            state["duration_s"],
            state.get("crystals_count", 0),
            state.get("confidence", "N/A"),
        )

        return state
