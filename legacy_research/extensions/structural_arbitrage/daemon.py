# [C5-REAL] Exergy-Maximized
"""
Arbitrage Daemon.
Sovereign Orchestrator (Persist-Executor) controlling the continuous observation-action loop.
"""

import asyncio
import logging
from typing import Protocol

from cortex.extensions.structural_arbitrage.kernel import ExecutionKernel
from cortex.extensions.structural_arbitrage.models import CortexAmount
from cortex.extensions.structural_arbitrage.scanner import InefficiencyScanner

log = logging.getLogger(__name__)


class SovereignOrchestrator(Protocol):
    """Protocol for integrating into CORTEX-Persist daemon manager."""
    async def run(self) -> None: ...


class ArbitrageDaemon:
    """
    Autopoiesis Watchdog Loop. Continually maps structural inefficiencies.
    Uses asynchronous native Python (asyncio). NO time.sleep().
    """

    def __init__(
        self,
        scanner: InefficiencyScanner,
        kernel: ExecutionKernel,
        venues: list[str],
        asset_pairs: list[str],
        interval_seconds: int = 5,
    ) -> None:
        self.scanner = scanner
        self.kernel = kernel
        self.venues = venues
        self.asset_pairs = asset_pairs
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        log.info("ArbitrageDaemon iniciado: Sovereign C5-REAL.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("ArbitrageDaemon detenido (Apoptosis celular).")

    async def _loop(self) -> None:
        try:
            while self._running:
                for pair in self.asset_pairs:
                    signals = await self.scanner.scan_pair(pair, self.venues)
                    for signal in signals:
                        result = await self.kernel.execute_signal(signal)
                        if result.success:
                            # Aserción estructural completada.
                            pass
                
                await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            log.info("Bucle de ArbitrageDaemon cancelado por interrupción del sistema.")
            raise
        except Exception as e:
            log.error(f"Fallo P0 en ArbitrageDaemon: {str(e)}. Apoptosis requerida.")
            self._running = False
