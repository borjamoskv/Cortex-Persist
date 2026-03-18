"""
verification_agent.py — VerificationAgent

Reactive agent wrapping SovereignVerifier. Receives TASK_REQUEST messages
with code + context payloads, runs invariant checks, returns TASK_RESULT.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.verification.verifier import SovereignVerifier, VerificationResult

logger = logging.getLogger(__name__)


class VerificationAgent(BaseAgent):
    """Reactive agent — runs deterministic invariant checks on code proposals."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: SqliteMessageBus,
        tool_registry: ToolRegistry,
        verifier: SovereignVerifier | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._verifier = verifier or SovereignVerifier()

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        code: str = payload.get("code", "")
        context: dict[str, Any] = payload.get("context", {})

        if not code:
            await self._reply(message, {"error": "missing required field: code"})
            return

        try:
            result: VerificationResult = self._verifier.check(code, context)
            await self._reply(
                message,
                {
                    "is_valid": result.is_valid,
                    "violations": result.violations,
                    "proof_certificate": result.proof_certificate,
                    "counterexample": result.counterexample,
                },
            )
        except Exception as exc:
            logger.exception("VerificationAgent check failed")
            await self._reply(message, {"error": str(exc)})

    async def tick(self) -> None:
        logger.debug("VerificationAgent tick — idle")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)
