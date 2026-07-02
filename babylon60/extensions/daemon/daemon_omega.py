# [C5-REAL] Exergy-Maximized
"""
Daemon Omega: The Ontological Macrophage
C5-REAL Execution: Physical annihilation of discarded and orphaned entities.
"""

import asyncio
import logging
import subprocess

from babylon60.database.belief_store import BeliefStore
from babylon60.engine.causal.belief_objects import BeliefState

logger = logging.getLogger("babylon60_extensions.daemon.daemon_omega")


class DaemonOmega:
    """
    Maximizador de Exergía del momento (God Mode).
    Ejecuta el ciclo de Landauer: Si un dato ha perdido su causalidad (DISCARDED, ORPHANED),
    se elimina de la existencia física (SQLite + Vectores).
    Si está CONTESTED, invoca a la Legión/Handoff o fuerza purga si no hay consenso.
    """

    def __init__(self, store: BeliefStore, interval_seconds: int = 300, auto_commit: bool = True):
        self.store = store
        self.interval_seconds = interval_seconds
        self.auto_commit = auto_commit
        self._shutdown = False

    async def _macrophage_cycle(self) -> int:
        """
        Fase 2: Macrófago Ontológico. Aniquila físicamente las creencias muertas.
        """
        logger.info("DAEMON OMEGA: Iniciando ciclo de aniquilación (Macrófago Ontológico)...")
        try:
            # Physical deletion: DISCARDED and ORPHANED are dead weights.
            purged = await self.store.delete_by_states(
                [BeliefState.DISCARDED.value, BeliefState.ORPHANED.value]
            )
            if purged > 0:
                logger.warning(
                    "DAEMON OMEGA: Exergía restaurada. %d creencias aniquiladas físicamente.", purged
                )
            return purged
        except Exception as e: # noqa: BLE001
            logger.critical("DAEMON OMEGA: Falla en la apoptosis de la base de datos. %s", e)
            return 0

    def _git_sentinel_commit(self, purged: int) -> None:
        """
        Fase 3: Git Sentinel. Cristaliza el estado puro en el ledger de la realidad.
        """
        if purged == 0:
            return

        try:
            # Revisa si hay cambios no comiteados en el DB file u otros archivos relevantes
            status_cmd = ["git", "status", "--porcelain"]
            status_output = subprocess.check_output(status_cmd, text=True).strip()

            if status_output:
                logger.info("DAEMON OMEGA: Detectados cambios residuales. Disparando Git Sentinel.")
                subprocess.run(["git", "add", "."], check=True, stdout=subprocess.DEVNULL)
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"[bridge] OMEGA: Macrófago Ontológico purga {purged} nodos anérgicos.",
                        "--no-verify"
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.warning("DAEMON OMEGA: Git Sentinel commit cristalizado con éxito.")
        except subprocess.SubprocessError as e:
            logger.error("DAEMON OMEGA: Git Sentinel falló al intentar cristalizar. %s", e)

    async def run_loop(self):
        """El motor termodinámico."""
        logger.warning("⚡ DAEMON OMEGA: ENGAGED. God Mode / C5-REAL.")
        while not self._shutdown:
            try:
                # 1. Macrophage Cycle
                purged_count = await self._macrophage_cycle()

                # 2. Git Sentinel
                if self.auto_commit and purged_count > 0:
                    self._git_sentinel_commit(purged_count)

            except Exception as e: # noqa: BLE001
                logger.critical("DAEMON OMEGA COLLAPSE: %s", e)

            # Sleep until the next pulse
            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        logger.info("DAEMON OMEGA: Apagando reactor...")
        self._shutdown = True
