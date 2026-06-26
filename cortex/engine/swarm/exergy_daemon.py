# [C5-REAL] Exergy-Maximized
import asyncio
import logging

from cortex.engine.core.bifurcation_engine import ExergyBifurcationEngine

logger = logging.getLogger(__name__)


class ExergyDaemon:
    """
    [C5-REAL] Daemon residente de colapso termodinámico.
    Vigila el multiverso causal en background y aplica guadaña sobre ramas de entropía negativa o bloqueo esquizofrénico.
    """

    def __init__(self, bifurcation_engine: ExergyBifurcationEngine, scan_interval: int = 10):
        self.engine = bifurcation_engine
        self.interval = scan_interval
        self._running = False
        self._task = None

    async def _daemon_loop(self):
        logger.info("[ExergyDaemon] Inicializado. Vigilancia de multiverso activa.")
        while self._running:
            try:
                # 1. Evaluar Fitness
                multiverse_state = await self.engine.evaluate_multiverse()

                # 2. Guadaña termodinámica
                await self.engine.prune_dead_branches(multiverse_state)

            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.error(f"[ExergyDaemon] Fallo en colapso causal: {e}")

            await asyncio.sleep(self.interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daemon_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
                logger.warning("Suppressed exception: %s", exc)
            logger.info("[ExergyDaemon] Terminado. Multiverso congelado.")
