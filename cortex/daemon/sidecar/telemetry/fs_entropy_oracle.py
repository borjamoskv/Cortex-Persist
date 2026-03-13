from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine


class FSEntropyOracle:
    def __init__(
        self,
        engine: AsyncCortexEngine,
        target_dir: str | Path,
        poll_interval: float = 3600.0,
        entropy_threshold_mb: float = 50.0,
    ) -> None:
        self.engine = engine
        self.target_dir = Path(target_dir)
        self.poll_interval = poll_interval
        self.entropy_threshold_mb = entropy_threshold_mb
        self._running = False
        self._baseline_mass = -1.0

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._measure_entropy()
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        self._running = False
        await asyncio.sleep(0)

    async def _measure_entropy(self) -> None:
        if not self.target_dir.exists():
            return

        current_mass = sum(
            f.stat().st_size
            for f in self.target_dir.rglob("*")
            if f.is_file() and "__pycache__" not in f.parts and ".git" not in f.parts
        ) / (1024 * 1024)

        if self._baseline_mass < 0:
            self._baseline_mass = current_mass
            return

        delta = current_mass - self._baseline_mass

        if delta > self.entropy_threshold_mb:
            content = (
                f"ENTROPÍA EN EXPANSIÓN. Acumulación de masa muerta o "
                f"datos no procesados: +{delta:.2f} MB."
            )
            if hasattr(self.engine, "store") and asyncio.iscoroutinefunction(self.engine.store):
                await self.engine.store(
                    project="SYSTEM",
                    content=content,
                    fact_type="ghost",
                    meta={
                        "oracle": "fs_entropy_v1",
                        "baseline_mb": self._baseline_mass,
                        "current_mb": current_mass,
                        "delta_mb": delta,
                        "target_dir": str(self.target_dir),
                    },
                )
            else:
                self.engine.store_sync(
                    project="SYSTEM",
                    content=content,
                    fact_type="ghost",
                    meta={
                        "oracle": "fs_entropy_v1",
                        "baseline_mb": self._baseline_mass,
                        "current_mb": current_mass,
                        "delta_mb": delta,
                        "target_dir": str(self.target_dir),
                    },
                )
            self._baseline_mass = current_mass
