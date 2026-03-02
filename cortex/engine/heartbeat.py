"""Heartbeat Emitter — Stateless signaling for CORTEX processes.

Follows the 130/100 standard: Zero-latency, idempotent, structured telemetry.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from cortex.nexus_v8 import DomainOrigin, IntentType, NexusWorldModel, Priority, WorldMutation
from cortex.utils import hygiene
from cortex.utils.semantic_heartbeat import SemanticHeartbeat

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine

logger = logging.getLogger("cortex.heartbeat")


class HeartbeatEmitter:
    """Pulses the CORTEX Heartbeat via the Nexus Signaling Bus."""

    def __init__(self, nexus: NexusWorldModel, engine: AsyncCortexEngine, project: str):
        self._nexus = nexus
        self._engine = engine
        self._project = project
        self._is_active = False
        self._semantic = SemanticHeartbeat()

    async def start(self, interval: int = 300) -> None:
        """..."""
        if self._is_active:
            return
        self._is_active = True
        logger.info("[HEARTBEAT] Initiating Stateless Signaling on %s.", self._project)

        while self._is_active:
            await self.pulse()
            await asyncio.sleep(interval)

    async def pulse(self) -> bool:
        """Single heartbeat pulse with zero-latency semantic drift analysis."""
        try:
            # Gather health metrics with a strict timeout to ensure zero-latency
            # in the main execution paths.
            health = await asyncio.wait_for(
                asyncio.to_thread(hygiene.check_system_health),
                timeout=2.0
            )
        except Exception as e:
            logger.warning("[HEARTBEAT] Health gathering timed out or failed: %s", e)
            health = {"status": "degraded", "error": str(e)}

        drift = self._semantic.calculate_drift(health)

        # Determine urgency: if drift exceeds threshold, escalate priority
        priority = Priority.NORMAL if drift < self._semantic.threshold else Priority.HIGH

        logger.info(
            "[HEARTBEAT] Pulsing %s. Drift: %.2f (Threshold: %.2f)",
            self._project, drift, self._semantic.threshold
        )

        return await self._nexus.mutate(WorldMutation(
            origin=DomainOrigin.CORTEX_CORE,
            intent=IntentType.HEARTBEAT_PULSE,
            project=self._project,
            priority=priority,
            payload={
                "hygiene": health,
                "semantic_drift": drift,
                "engine_status": "active",
                "reason": "Stable state" if priority == Priority.NORMAL
                else "SEMANTIC DRIFT DETECTED",
            },
        ))

    def stop(self) -> None:
        """Stop the heartbeat."""
        self._is_active = False
        logger.info("[HEARTBEAT] Hibernating.")
