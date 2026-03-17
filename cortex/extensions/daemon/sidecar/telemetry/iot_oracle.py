"""SOVEREIGN IOT TELEMETRY ORACLE (CORTEX Sidecar)
Physical-Cognitive Entanglement — tensor-robocar-entanglement

Captures physical friction and acts as the bridging protocol between hardware
(NXP, ESP32, environmental sensors) and the CORTEX core.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.engine_async import AsyncCortexEngine

logger = logging.getLogger("cortex.sidecar.telemetry.iot_oracle")


class IoTOracle:
    """
    Sovereign Physical Telemetry Oracle.

    Establishes the bridge between biological/physical signals (Temperature, Movement, MQTT)
    and the CORTEX Sovereign Ledger.
    """

    def __init__(
        self,
        engine: CortexEngine | AsyncCortexEngine,
        poll_interval: float = 10.0,
        enable_simulated_sensors: bool = True,
    ):
        self.engine = engine
        self.poll_interval = poll_interval
        self._running = False
        self.enable_simulated_sensors = enable_simulated_sensors
        # Simulates R-Value dropping in an Earthship MMX or a Robocar friction event.
        self._sim_temp = 22.0

    async def start(self) -> None:
        """Invokes the Oracle's physical sensors."""
        self._running = True
        logger.info("📡 IOT ORACLE ONLINE. Physical Entanglement Active.")

        while self._running:
            try:
                await self._process_telemetry()
            except Exception as e:
                logger.error("IOT ORACLE SENSOR FAILURE: %s", e)
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Closes the Oracle's bridge to the physical world."""
        self._running = False
        logger.info("IOT ORACLE OFFLINE.")

    async def _process_telemetry(self) -> None:
        """Fetches data from edge devices and crystallizes friction."""
        if not self.enable_simulated_sensors:
            return  # In production, this would poll over MQTT / WebSocket to NXP

        # Simulated Earthship or Robocar thermal friction
        self._sim_temp -= 0.1  # Entropy drop

        if self._sim_temp < 18.0:
            logger.warning(
                "🌡️ [IOT ORACLE] Thermodynamic Friction Detected: Temp dropped to %.2f",
                self._sim_temp,
            )
            await self._inject_physical_intent(
                friction_type="thermal_drop",
                severity="P2",
                metrics={"temperature": self._sim_temp, "r_value": 0.85},
            )
            self._sim_temp = 22.0  # Simulated physical auto-actuation (e.g. heating loop activated)

    async def _inject_physical_intent(
        self, friction_type: str, severity: str, metrics: dict[str, Any]
    ) -> None:
        """Collapses the physical friction into a CORTEX Sovereign Fact."""
        content = (
            f"Fricción Física Detectada en el Entorno (Edge Node).\n"
            f"Tipo: {friction_type}\n"
            f"Gravedad: {severity}\n"
            f"Métricas: {metrics}"
        )

        try:
            # We must handle both sync and async engine types depending on how sidecars are initialized
            if hasattr(self.engine, "store") and asyncio.iscoroutinefunction(self.engine.store):
                await self.engine.store(
                    project="earthship_mmx",
                    content=content,
                    fact_type="physical_telemetry",
                    meta={
                        "oracle": "iot_oracle_v1",
                        "friction_type": friction_type,
                        "metrics": metrics,
                        "severity": severity,
                    },
                )
            else:
                self.engine.store_sync(  # type: ignore[type-error]
                    project="earthship_mmx",
                    content=content,
                    fact_type="physical_telemetry",
                    meta={
                        "oracle": "iot_oracle_v1",
                        "friction_type": friction_type,
                        "metrics": metrics,
                        "severity": severity,
                    },
                )
            logger.info("🧠 [IOT ORACLE] Entanglement Collapsed: %s -> %s", friction_type, severity)
        except Exception as e:
            logger.error("IOT Oracle Injection failed: %s", e)
