# [C5-REAL] Exergy-Maximized
import asyncio
import logging
from typing import Any

logger = logging.getLogger("cortex.engine.uncategorized.event_sovereignty")


class EventSovereigntyRuntime:
    """
    HITO 34: Persistent Event Sovereignty.
    Transitioning from reactive cron jobs to an asynchronous event-driven loop.
    Wakes up immediately on events to compute state, check anomalies, and emit
    authorization requests if required.
    """

    def __init__(self, event_bus: Any, anomaly_bridge: Any = None, auth_gateway: Any = None):
        self.event_bus = event_bus
        self.anomaly_bridge = anomaly_bridge
        self.auth_gateway = auth_gateway
        self._running = False

    async def start(self) -> None:
        """Starts the sovereignty runtime, subscribing to core events."""
        logger.info("🚀 Starting EventSovereigntyRuntime...")
        self._running = True

        # Subscribe to relevant telemetry/system events
        self.event_bus.subscribe("system.telemetry", self._handle_telemetry_event)
        self.event_bus.subscribe("system.alert", self._handle_alert_event)

        # We can also keep a scheduled observation task running in parallel
        # to ensure the system is not fully dependent on external pulses.
        asyncio.create_task(self._scheduled_observation_loop())

    async def stop(self) -> None:
        """Gracefully stops the runtime."""
        logger.info("Stopping EventSovereigntyRuntime...")
        self._running = False

    async def _handle_telemetry_event(self, payload: dict[str, Any]) -> None:
        """Called immediately when a telemetry event is emitted."""
        logger.debug("[SovereigntyRuntime] Received telemetry event: %s", payload)
        await self._process_state(payload)

    async def _handle_alert_event(self, payload: dict[str, Any]) -> None:
        """Called immediately when a critical alert event is emitted."""
        logger.warning("[SovereigntyRuntime] Received alert event: %s", payload)
        await self._process_state(payload, is_alert=True)

    async def _process_state(self, state: dict[str, Any], is_alert: bool = False) -> None:
        """Processes the state using the anomaly bridge."""
        if not self.anomaly_bridge:
            return

        is_anomalous = await self.anomaly_bridge.detect_anomaly(state)
        if is_anomalous or is_alert:
            logger.warning("Anomaly detected. Generating hypothesis and requesting override...")
            if self.auth_gateway:
                hypothesis = "Detected critical entropy deviation. Propose structural mitigation."
                await self.auth_gateway.request_override(hypothesis, state)

    async def _scheduled_observation_loop(self) -> None:
        """Ensures the system still has a pulse even if no external events arrive."""
        while self._running:
            try:
                # Polling frequency for scheduled observation
                await asyncio.sleep(60)
                # Emit a heartbeat/observation event to the bus to trigger self-auditing
                await self.event_bus.publish(
                    "system.telemetry",
                    {
                        "source": "sovereignty_daemon",
                        "action": "scheduled_observation",
                        "status": "ok",
                    },
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduled observation loop error: %s", e)
