"""Heartbeat Emitter — Stateless signaling with idle-triggered sleep.

Follows the 130/100 standard: Zero-latency, idempotent, structured telemetry.
When the system is idle for N seconds, triggers SleepOrchestrator for
memory consolidation — converting dead time into active learning,
exactly like biological sleep.

Derivation: Ω₅ (Antifragile) — idle periods STRENGTHEN the system.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from cortex.nexus_v8 import DomainOrigin, IntentType, NexusWorldModel, Priority, WorldMutation
from cortex.utils import hygiene
from cortex.utils.semantic_heartbeat import SemanticHeartbeat

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine
    from cortex.memory.sleep import SleepOrchestrator

logger = logging.getLogger("cortex.heartbeat")

# ─── Defaults ──────────────────────────────────────────────────────────

_DEFAULT_IDLE_THRESHOLD_S: float = 600.0   # 10 minutes idle → trigger sleep
_DEFAULT_SLEEP_COOLDOWN_S: float = 3600.0  # 1 hour minimum between sleep cycles


class HeartbeatEmitter:
    """Pulses the CORTEX Heartbeat via the Nexus Signaling Bus.

    When a SleepOrchestrator is injected, idle periods (zero semantic
    drift for ``idle_threshold_s`` seconds) automatically trigger a
    full NREM → REM → Calibration consolidation cycle.
    """

    __slots__ = (
        "_engine",
        "_idle_threshold_s",
        "_is_active",
        "_last_activity_at",
        "_last_sleep_at",
        "_nexus",
        "_project",
        "_semantic",
        "_sleep",
        "_sleep_cooldown_s",
    )

    def __init__(
        self,
        nexus: NexusWorldModel,
        engine: AsyncCortexEngine,
        project: str,
        *,
        sleep: SleepOrchestrator | None = None,
        idle_threshold_s: float = _DEFAULT_IDLE_THRESHOLD_S,
        sleep_cooldown_s: float = _DEFAULT_SLEEP_COOLDOWN_S,
    ):
        self._nexus = nexus
        self._engine = engine
        self._project = project
        self._is_active = False
        self._semantic = SemanticHeartbeat()

        # Sleep integration
        self._sleep = sleep
        self._idle_threshold_s = idle_threshold_s
        self._sleep_cooldown_s = sleep_cooldown_s
        self._last_activity_at: float = time.monotonic()
        self._last_sleep_at: float = 0.0  # epoch = never slept

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
        """Single heartbeat pulse with zero-latency semantic drift analysis.

        If drift is zero for longer than ``idle_threshold_s`` and a
        ``SleepOrchestrator`` is attached, triggers a full consolidation
        cycle and emits it to the Nexus bus.
        """
        try:
            # Gather health metrics with a strict timeout to ensure zero-latency
            # in the main execution paths.
            health = await asyncio.wait_for(
                asyncio.to_thread(hygiene.check_system_health), timeout=2.0
            )
        except (TimeoutError, OSError, RuntimeError) as e:
            logger.warning("[HEARTBEAT] Health gathering timed out or failed: %s", e)
            health = {"status": "degraded", "error": str(e)}

        drift = self._semantic.calculate_drift(health)

        # ── Idle tracking ─────────────────────────────────────────
        now = time.monotonic()
        if drift > 0:
            self._last_activity_at = now  # system state changed → not idle

        # ── Sleep trigger ─────────────────────────────────────────
        await self._maybe_trigger_sleep(now)

        # Determine urgency: if drift exceeds threshold, escalate priority
        priority = Priority.NORMAL if drift < self._semantic.threshold else Priority.HIGH

        logger.info(
            "[HEARTBEAT] Pulsing %s. Drift: %.2f (Threshold: %.2f)",
            self._project,
            drift,
            self._semantic.threshold,
        )

        return await self._nexus.mutate(
            WorldMutation(
                origin=DomainOrigin.CORTEX_CORE,
                intent=IntentType.HEARTBEAT_PULSE,
                project=self._project,
                priority=priority,
                payload={
                    "hygiene": health,
                    "semantic_drift": drift,
                    "engine_status": "active",
                    "reason": "Stable state"
                    if priority == Priority.NORMAL
                    else "SEMANTIC DRIFT DETECTED",
                },
            )
        )

    async def _maybe_trigger_sleep(self, now: float) -> None:
        """Evaluate idle conditions and trigger sleep cycle if appropriate.

        Guards:
          1. SleepOrchestrator must be attached
          2. Idle time must exceed threshold
          3. Cooldown from last sleep must have elapsed
        """
        if self._sleep is None:
            return

        idle_seconds = now - self._last_activity_at
        if idle_seconds < self._idle_threshold_s:
            return

        cooldown_elapsed = (now - self._last_sleep_at) > self._sleep_cooldown_s
        if not cooldown_elapsed:
            return

        # ── Trigger consolidation ─────────────────────────────────
        logger.info(
            "[HEARTBEAT] System idle for %.0fs (threshold: %.0fs). "
            "Triggering sleep cycle for %s.",
            idle_seconds,
            self._idle_threshold_s,
            self._project,
        )

        try:
            report = await self._sleep.run_full_cycle(self._project)
            self._last_sleep_at = time.monotonic()
            self._last_activity_at = time.monotonic()  # reset idle after consolidation

            # Emit sleep event to Nexus
            await self._nexus.mutate(
                WorldMutation(
                    origin=DomainOrigin.CORTEX_CORE,
                    intent=IntentType.SLEEP_CYCLE_TRIGGERED,
                    project=self._project,
                    priority=Priority.LOW,
                    payload={
                        "idle_seconds": idle_seconds,
                        "nrem_merged": report.nrem_merged,
                        "nrem_reinforced": report.nrem_reinforced,
                        "nrem_conflicts": report.nrem_conflicts,
                        "rem_clusters": report.rem_clusters_found,
                        "rem_bridges": report.rem_bridges_created,
                        "brier_before": report.brier_before,
                        "brier_after": report.brier_after,
                        "fok_adjusted": report.threshold_adjusted,
                        "total_duration_ms": report.total_duration_ms,
                    },
                )
            )

            logger.info(
                "[HEARTBEAT] Sleep cycle complete for %s. "
                "NREM: merged=%d reinforced=%d | REM: clusters=%d bridges=%d | "
                "Brier: %.4f → %.4f",
                self._project,
                report.nrem_merged,
                report.nrem_reinforced,
                report.rem_clusters_found,
                report.rem_bridges_created,
                report.brier_before,
                report.brier_after,
            )

        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning(
                "[HEARTBEAT] Sleep cycle failed for %s: %s", self._project, exc
            )

    def stop(self) -> None:
        """Stop the heartbeat."""
        self._is_active = False
        logger.info("[HEARTBEAT] Hibernating.")
