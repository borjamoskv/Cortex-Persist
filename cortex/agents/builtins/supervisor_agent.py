"""
supervisor_agent.py — SupervisorAgent

Reactive agent that wraps the Supervisor to provide a message-based control
plane for agent lifecycle operations: start, stop, quarantine, status.
External callers can request lifecycle operations via TASK_REQUEST messages
instead of calling the Supervisor directly.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)

_OPS: frozenset[str] = frozenset({"start", "stop", "quarantine", "status", "health"})


class SupervisorAgent(BaseAgent):
    """Reactive agent — exposes Supervisor lifecycle ops over the message bus."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: SqliteMessageBus,
        tool_registry: ToolRegistry,
        supervisor: Supervisor,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._supervisor = supervisor

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        op: str = payload.get("op", "")

        if op not in _OPS:
            await self._reply(message, {"error": f"unknown op: {op!r}", "supported": sorted(_OPS)})
            return

        try:
            result = await self._dispatch(op, payload)
            await self._reply(message, {"op": op, "result": result})
        except Exception as exc:
            logger.exception("SupervisorAgent op=%s failed", op)
            await self._reply(message, {"op": op, "error": str(exc)})

    async def tick(self) -> None:
        """Periodic health-check tick — detects stale agents."""
        await self._supervisor.health_check()

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        agent_id: str = payload.get("agent_id", "")

        if op == "start":
            if not agent_id:
                raise ValueError("agent_id required for start")
            await self._supervisor.start_agent(agent_id)
            return {"started": agent_id}

        if op == "stop":
            if not agent_id:
                raise ValueError("agent_id required for stop")
            await self._supervisor.stop_agent(agent_id)
            return {"stopped": agent_id}

        if op == "quarantine":
            if not agent_id:
                raise ValueError("agent_id required for quarantine")
            await self._supervisor.quarantine_agent(agent_id)
            return {"quarantined": agent_id}

        if op == "status":
            return self._supervisor.status()

        if op == "health":
            await self._supervisor.health_check()
            return self._supervisor.status()

        raise ValueError(f"unhandled op: {op!r}")

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
