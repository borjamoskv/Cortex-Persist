"""
nightshift_agent.py — NightshiftAgent

Daemon agent wrapping NightShiftCrystalDaemon. On each tick it runs one
consolidation cycle, emits a FACT_PROPOSAL per crystal produced, and
publishes cycle reports to configured escalation targets.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.extensions.swarm.nightshift_daemon import NightShiftCrystalDaemon

logger = logging.getLogger(__name__)


class NightshiftAgent(BaseAgent):
    """Daemon agent — drives NightShiftCrystalDaemon on each autonomous tick.

    Emits FACT_PROPOSAL for every crystal synthesized, then broadcasts
    a cycle summary to escalation_targets.
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: SqliteMessageBus,
        tool_registry: ToolRegistry,
        daemon: NightShiftCrystalDaemon | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._daemon = daemon or NightShiftCrystalDaemon()

    # ------------------------------------------------------------------
    # Daemon tick — run one consolidation cycle
    # ------------------------------------------------------------------

    async def tick(self) -> None:
        logger.info("NightshiftAgent — starting consolidation cycle")
        try:
            report: dict[str, Any] = await self._daemon.run_cycle()
        except Exception as exc:
            logger.exception("NightshiftAgent — run_cycle() failed")
            raise RuntimeError(f"NightShiftCrystalDaemon failure: {exc}") from exc

        crystals: list[Any] = report.get("crystals", [])
        logger.info("NightshiftAgent — cycle complete, %d crystal(s)", len(crystals))

        for crystal in crystals:
            await self._emit_crystal(crystal)

        await self._publish_summary(report)

    # ------------------------------------------------------------------
    # Ignore incoming task requests (daemon-only agent)
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind == MessageKind.SHUTDOWN:
            logger.info("NightshiftAgent — shutdown requested by %s", message.sender)
            self._daemon.stop()
            self.force_stop()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _emit_crystal(self, crystal: Any) -> None:
        msg = new_message(
            sender=self.manifest.agent_id,
            recipient="memory_agent",
            kind=MessageKind.FACT_PROPOSAL,
            payload={
                "source": "nightshift",
                "crystal": crystal if isinstance(crystal, dict) else str(crystal),
            },
        )
        await self.bus.send(msg)

    async def _publish_summary(self, report: dict[str, Any]) -> None:
        targets = self.manifest.escalation_targets or []
        for target in targets:
            msg = new_message(
                sender=self.manifest.agent_id,
                recipient=target,
                kind=MessageKind.TASK_RESULT,
                payload={"cycle_report": report},
            )
            await self.bus.send(msg)
