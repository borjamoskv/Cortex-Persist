"""
security_agent.py — SecurityAgent

Daemon agent wrapping SecurityMonitor. Runs periodic async security checks
on each tick, emits ALERT_ENTROPY messages for every security alert found.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.extensions.daemon.monitors.security import SecurityMonitor

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """Daemon agent — runs SecurityMonitor.check_async() on every tick.

    Emits ALERT_ENTROPY to all escalation_targets when threats are detected.
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: SqliteMessageBus,
        tool_registry: ToolRegistry,
        monitor: SecurityMonitor | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._monitor = monitor or SecurityMonitor()

    # ------------------------------------------------------------------
    # Daemon tick — main security scan
    # ------------------------------------------------------------------

    async def tick(self) -> None:
        try:
            alerts = await self._monitor.check_async()
        except Exception as exc:
            logger.exception("SecurityAgent monitor.check_async() failed")
            raise RuntimeError(f"SecurityMonitor failure: {exc}") from exc

        if not alerts:
            logger.debug("SecurityAgent tick — no threats detected")
            return

        logger.warning("SecurityAgent — %d alert(s) detected", len(alerts))
        for alert in alerts:
            await self._broadcast_alert(alert)

    # ------------------------------------------------------------------
    # Handle incoming TASK_REQUEST (on-demand scan)
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        if payload.get("op") == "scan":
            await self.tick()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _broadcast_alert(self, alert: Any) -> None:
        targets = self.manifest.escalation_targets or []
        if not targets:
            logger.warning("SecurityAgent — no escalation_targets configured")
            return

        for target in targets:
            msg = new_message(
                sender=self.manifest.agent_id,
                recipient=target,
                kind=MessageKind.ALERT_ENTROPY,
                payload={
                    "source": "security_monitor",
                    "severity": getattr(alert, "severity", "unknown"),
                    "description": str(alert),
                },
            )
            await self.bus.send(msg)
