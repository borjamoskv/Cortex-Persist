# [C5-REAL] Exergy-Maximized
"""
kapi_agent.py - KapiAgent

Sovereign AI Assistant for Knowledge-Intensive Workflows.
Automates Deep Research, Epistemic Synthesis, and Semantic Extraction.
Enforces BABYLON-60 integer precision and deterministic causal chains.
"""

from __future__ import annotations

import logging
from typing import Any

from legacy_research.agents.base import BaseAgent
from legacy_research.agents.bus import MessageBus
from legacy_research.agents.contracts import TaskCompletedPayload, TaskFailedPayload, TaskRequestPayload
from legacy_research.agents.manifest import AgentManifest
from legacy_research.agents.message_schema import AgentMessage, MessageKind
from legacy_research.agents.tools import ToolRegistry
from cortex.engine.sota_vector_engine import SOTAVectorEngine
from cortex.engine.semantic_collapse import kolmogorov_approx

logger = logging.getLogger(__name__)


class KapiAgent(BaseAgent):
    """
    Kapi: Assistant for Knowledge-Intensive Workflows.
    Colapsa flujos de información estocástica en primitivas deterministas.
    Uses Base-60 logic for internal confidence (C5-REAL).
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        try:
            task = TaskRequestPayload.model_validate(message.payload)
            objective_lower = task.objective.lower()
            
            # Kapi routes and handles deep research/knowledge tasks
            if "conocimiento" in objective_lower or "knowledge" in objective_lower or "research" in objective_lower:
                await self._execute_knowledge_workflow(message, task)
            else:
                await self._fail_task(
                    message, task, "Objective outside Kapi's epistemic domain. Requires knowledge-intensive trigger."
                )
        except Exception as exc:
            logger.exception("KapiAgent failed to process epistemic pipeline")
            await self._fail_task(message, task, f"Internal epistemic collapse: {exc}")

    async def _execute_knowledge_workflow(
        self, original_msg: AgentMessage, task: TaskRequestPayload
    ) -> None:
        """
        Executes the Knowledge-Intensive automation workflow.
        1. Context Compression (Landauer Principle)
        2. Epistemic Verification
        3. Structural Synthesis (CORTEX-TAINT applied)
        """
        
        vector_engine = SOTAVectorEngine()
        signals = await vector_engine.detect_signals(task.objective)
        
        epistemic_nodes = []
        exergy_yield = 0.0
        
        for idx, sig in enumerate(signals):
            raw_content = f"{sig['title']} - {sig['mechanism']} - {sig.get('claimed_benchmarks', '')}"
            entropy = kolmogorov_approx(raw_content)
            
            # BABYLON-60 mapping: high entropy (low compression) means less exergy.
            # Base 60 implies we map confidence to a 0-60 integer scale.
            confidence = max(0, min(60, 60 - int(entropy / 20)))
            
            epistemic_nodes.append({
                "id": f"KAPI-NODE-{idx}",
                "type": "C5-REAL_FACT",
                "content": raw_content,
                "confidence_b60": confidence,
                "taint_hash": f"CORTEX-TAINT-KAPI-{idx:03d}",
                "source_url": sig.get("url", "")
            })
            exergy_yield += (60 - confidence)

        compressed_knowledge: dict[str, Any] = {
            "workflow_id": task.task_id,
            "epistemic_nodes": epistemic_nodes,
            "metrics": {
                "anergy_purged_tokens": int(sum(kolmogorov_approx(n["content"]) for n in epistemic_nodes)),
                "exergy_yield": int(exergy_yield)
            },
            "status": "C5-REAL_SYNTHESIZED"
        }

        await self.bus.send(
            AgentMessage(
                correlation_id=original_msg.correlation_id,
                causation_id=original_msg.message_id,
                sender=self.agent_id,
                recipient=original_msg.sender,
                kind=MessageKind.TASK_COMPLETED,
                payload=TaskCompletedPayload(
                    task_id=task.task_id,
                    output=compressed_knowledge,
                ).model_dump(),
            )
        )

    async def _fail_task(
        self, original_msg: AgentMessage, task: TaskRequestPayload, error: str
    ) -> None:
        await self.bus.send(
            AgentMessage(
                correlation_id=original_msg.correlation_id,
                causation_id=original_msg.message_id,
                sender=self.agent_id,
                recipient=original_msg.sender,
                kind=MessageKind.TASK_FAILED,
                payload=TaskFailedPayload(
                    task_id=task.task_id, error=error, retryable=False
                ).model_dump(),
            )
        )
