from __future__ import annotations

import asyncio
import os
import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine


class ThermodynamicsOracle:
    def __init__(
        self,
        engine: AsyncCortexEngine,
        poll_interval: float = 60.0,
        thermal_threshold: float = 0.85,
    ) -> None:
        self.engine = engine
        self.poll_interval = poll_interval
        self.thermal_threshold = thermal_threshold
        self._running = False
        self._cores = os.cpu_count() or 1

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._sample_thermodynamics()
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        self._running = False
        await asyncio.sleep(0)

    async def _sample_thermodynamics(self) -> None:
        if platform.system() == "Windows":
            return

        load1, load5, _ = os.getloadavg()
        utilization = load1 / self._cores

        if utilization > self.thermal_threshold:
            content = (
                f"INCENDIO TERMODINÁMICO. Sobrecarga bruta. "
                f"Load1: {load1:.2f} (Cores: {self._cores})."
            )
            if hasattr(self.engine, "store") and asyncio.iscoroutinefunction(self.engine.store):
                await self.engine.store(
                    project="SYSTEM",
                    content=content,
                    fact_type="thermal_noise",
                    meta={
                        "oracle": "thermodynamics_v1",
                        "load1": load1,
                        "load5": load5,
                        "utilization": utilization,
                        "cores": self._cores,
                        "severity": "CRITICAL" if utilization > 1.5 else "HIGH",
                    },
                )
            else:
                self.engine.store_sync(  # type: ignore[type-error]
                    project="SYSTEM",
                    content=content,
                    fact_type="thermal_noise",
                    meta={
                        "oracle": "thermodynamics_v1",
                        "load1": load1,
                        "load5": load5,
                        "utilization": utilization,
                        "cores": self._cores,
                        "severity": "CRITICAL" if utilization > 1.5 else "HIGH",
                    },
                )
