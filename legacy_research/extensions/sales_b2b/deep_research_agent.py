# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - B2B Deep Research Agent.

Integrates the Deep Research methodology to B2B outbound automation.
Overcomes context limits by compressing historical message trails into
structural invariants using the ContextCompressor.

Extends the Level 4 AutonomousAgent.
"""

from __future__ import annotations

import logging
from typing import Any

from legacy_research.agents.autonomous import AutonomousAgent
from legacy_research.agents.manifest import AgentManifest
from legacy_research.agents.message_schema import AgentMessage, MessageKind, new_message
from legacy_research.agents.tools import ToolRegistry
from legacy_research.extensions.sales_b2b.context_compressor import ContextCompressor
from legacy_research.extensions.sales_b2b.messaging_flow import MessagingFSM, MessagingStage

logger = logging.getLogger("cortex.extensions.sales_b2b.deep_research_agent")


class B2BDeepResearchAgent(AutonomousAgent):
    """B2B Automation Agent powered by Deep Research capabilities."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,
        tool_registry: ToolRegistry | None = None,
        *,
        max_plan_steps: int = 50,
        step_timeout_s: float = 30.0,
    ) -> None:
        super().__init__(
            manifest,
            bus,
            tool_registry,
            max_plan_steps=max_plan_steps,
            step_timeout_s=step_timeout_s,
        )
        self.compressor = ContextCompressor(entropy_threshold=2000)
        self.fsm = MessagingFSM()

    async def _handle_task_request(self, message: AgentMessage) -> None:
        """Override to intercept B2B specific payloads before L4 execution."""
        payload = message.payload or {}
        task_type = payload.get("type", "")

        if task_type == "PROCESS_LEAD":
            await self._process_lead(message, payload)
        else:
            # Fallback to standard AutonomousAgent behavior
            await super()._handle_task_request(message)

    async def _process_lead(self, message: AgentMessage, payload: dict[str, Any]) -> None:
        """
        Execute Deep Research and messaging state machine for a lead.
        Applies thermodynamic compression if the context is rotting.
        """
        lead_id = payload.get("lead_id", "unknown")
        history = payload.get("interaction_history", [])
        current_stage_str = payload.get("current_stage", "PROSPECTING")
        mtk_token = payload.get("mtk_token")  # Required for MTK transition
        
        try:
            current_stage = MessagingStage(current_stage_str)
        except ValueError:
            current_stage = MessagingStage.PROSPECTING
            
        logger.info("[%s] Processing lead %s at stage %s", self.agent_id, lead_id, current_stage.value)
        
        # 1. Compress context if limits exceeded
        history_str = str(history)
        if self.compressor.is_degraded(history_str):
            logger.warning("[%s] Context limits exceeded for lead %s. Triggering compression.", self.agent_id, lead_id)
            compressed_invariants = self.compressor.compress_history(history, agent_id=self.agent_id)
            payload["compressed_context"] = compressed_invariants
            # Purge raw narrative history
            payload.pop("interaction_history", None)
            
        # 2. Advance FSM deterministically (Enforce MTK Boundary)
        event_data = payload.get("event_data", {})
        next_stage = self.fsm.advance_stage(current_stage, event_data, mtk_token=mtk_token)
        
        if next_stage != current_stage:
            logger.info("[%s] Transitioning %s: %s -> %s", self.agent_id, lead_id, current_stage.value, next_stage.value)
            
        # 3. If in DEEP_RESEARCH, execute specialized plan
        if next_stage == MessagingStage.DEEP_RESEARCH:
            await self._execute_deep_research(lead_id, payload)
            # FSM will advance in the callback of the research result
            return
            
        # 4. Return outcome
        result = {
            "lead_id": lead_id,
            "previous_stage": current_stage.value,
            "new_stage": next_stage.value,
            "action_taken": f"Advanced to {next_stage.value}",
        }
        
        if "compressed_context" in payload:
            result["compression_hash"] = payload["compressed_context"].get("compression_hash")
            result["taint_signature"] = payload["compressed_context"].get("taint_signature")

        await self._reply(message, result)

    async def _execute_deep_research(self, lead_id: str, payload: dict[str, Any]) -> None:
        """
        Emits an async TASK_REQUEST to the swarm for deep research.
        Complies with AX-044 (Active Inference).
        """
        logger.info("[%s] Emitting DEEP_RESEARCH request for lead %s", self.agent_id, lead_id)
        
        research_payload = {
            "op": "EXECUTE_RESEARCH",
            "target": lead_id,
            "context": payload.get("compressed_context", {}),
        }
        
        # Route to the SOTA Vector Engine or Search Worker
        await self.request_task(
            recipient="swarm_research_worker",
            task_payload=research_payload,
        )

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        """Helper to send result back to sender."""
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)
