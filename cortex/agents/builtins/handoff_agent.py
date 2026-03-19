"""
handoff_agent.py — HandoffAgent

Reactive agent coordinating inter-agent context transfer. Wraps
save_handoff and load_handoff — the full generate_handoff requires a live
CortexEngine, so callers must pass engine via manifest metadata or inject
generate_handoff callable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.extensions.agents.handoff import load_handoff, save_handoff

logger = logging.getLogger(__name__)


class HandoffAgent(BaseAgent):
    """Reactive agent — manages session context serialisation between agents.

    For full handoff generation (requires CortexEngine), callers should call
    generate_handoff(...) themselves and forward the result as a HANDOFF_REQUEST
    payload.
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: SqliteMessageBus,
        tool_registry: ToolRegistry,
        handoff_dir: Path | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._handoff_dir = handoff_dir or Path("~/.cortex/handoffs").expanduser()
        self._handoff_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind == MessageKind.HANDOFF_REQUEST:
            await self._handle_handoff_request(message)
        elif message.kind == MessageKind.TASK_REQUEST:
            await self._handle_task_request(message)

    # ------------------------------------------------------------------
    # Private handlers
    # ------------------------------------------------------------------

    async def _handle_handoff_request(self, message: AgentMessage) -> None:
        payload: dict[str, Any] = message.payload or {}
        handoff_data: dict[str, Any] = payload.get("handoff", {})

        if not handoff_data:
            await self._reply(
                message,
                {"error": "missing 'handoff' key in payload"},
                kind=MessageKind.TASK_RESULT,
            )
            return

        try:
            path = self._handoff_dir / f"{message.sender}_{message.message_id[:8]}.json"
            save_handoff(handoff_data, path=path)
            logger.info("HandoffAgent — saved handoff for %s → %s", message.sender, path)
            await self._reply(
                message,
                {"path": str(path), "saved": True},
                kind=MessageKind.HANDOFF_ACCEPTED,
            )
        except Exception as exc:
            logger.exception("HandoffAgent — save_handoff failed")
            await self._reply(
                message,
                {"error": str(exc)},
                kind=MessageKind.TASK_RESULT,
            )

    async def _handle_task_request(self, message: AgentMessage) -> None:
        payload: dict[str, Any] = message.payload or {}
        op = payload.get("op", "")

        if op == "load":
            path_str: str = payload.get("path", "")
            try:
                data = load_handoff(Path(path_str) if path_str else None)
                await self._reply(message, {"handoff": data}, kind=MessageKind.TASK_RESULT)
            except Exception as exc:
                await self._reply(message, {"error": str(exc)}, kind=MessageKind.TASK_RESULT)
        else:
            await self._reply(
                message,
                {"error": f"unknown op: {op!r}"},
                kind=MessageKind.TASK_RESULT,
            )

    async def tick(self) -> None:
        logger.debug("HandoffAgent tick — idle")

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    async def _reply(
        self,
        source: AgentMessage,
        payload: dict[str, Any],
        kind: MessageKind = MessageKind.TASK_RESULT,
    ) -> None:
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=kind,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)
