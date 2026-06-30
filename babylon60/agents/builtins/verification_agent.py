# [C5-REAL] Exergy-Maximized
"""
verification_agent.py - VerificationAgent

Reactive agent wrapping SovereignVerifier. Receives TASK_REQUEST messages
with code + context payloads, runs invariant checks, returns TASK_RESULT.
"""

from __future__ import annotations

import logging
from typing import Any

from babylon60.verification.oracle import VerificationOracle
from babylon60.verification.verifier import SovereignVerifier

from babylon60.agents.base import BaseAgent
from babylon60.agents.bus import MessageBus
from babylon60.agents.manifest import AgentManifest
from babylon60.agents.message_schema import AgentMessage, MessageKind, new_message
from babylon60.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)


class VerificationAgent(BaseAgent):
    """Reactive agent - runs deterministic invariant checks on code proposals."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        verifier: SovereignVerifier | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._verifier = verifier or SovereignVerifier()
        self._oracle = VerificationOracle(engine=None)

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        subject: str = payload.get("subject", "")
        candidate: dict[str, Any] = payload.get("candidate", {})
        code: str = payload.get("code", "")
        context: dict[str, Any] = payload.get("context", {})

        try:
            if subject and candidate:
                oracle_result = await self._oracle.verify(subject, candidate)
                await self._reply(
                    message,
                    {
                        "ok": oracle_result.ok,
                        "verdict": oracle_result.verdict,
                        "reasons": oracle_result.reasons,
                    },
                )
                return

            if code:
                check_result = self._verifier.check(code, context)
                await self._reply(
                    message,
                    {
                        "ok": check_result.is_valid,
                        "verdict": "accepted" if check_result.is_valid else "rejected",
                        "is_valid": check_result.is_valid,
                        "violations": check_result.violations,
                        "proof_certificate": check_result.proof_certificate,
                        "counterexample": check_result.counterexample,
                    },
                )
                return

            await self._reply(
                message,
                {"error": "missing required field: code or subject/candidate"},
            )
        except Exception as exc:
            logger.exception("VerificationAgent check failed")
            await self._reply(message, {"error": str(exc)})

    async def tick(self) -> None:
        logger.debug("VerificationAgent tick - idle")

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
