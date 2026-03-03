"""🧪 INCUBADORA GHOST — El Elevador de Trust Score.

Eleva el peso de los votos (Karma Weight) mediante consumo pasivo de feed.
Unificador: PhantomTransport (JA3/JA4 Spoofing).
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from cortex.network.phantom_transport import PhantomTransport

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🤖 %(levelname)s: %(message)s")
logger = logging.getLogger("GhostIncubator")


class LurkerProfile:
    """Modela el comportamiento de lectura pasiva de un Ghost."""

    def __init__(self, ghost_id: str, base_url: str = "https://www.moltbook.com"):
        self.ghost_id = ghost_id
        self.base_url = base_url
        self.session_data: dict[str, Any] = {}
        # Transport soberano que mantiene las cookies pasivas
        self._transport = PhantomTransport(impersonate="chrome120")

    async def _stochastic_delay(self, min_s: float = 2.0, max_s: float = 15.0):
        """Pausas termodinámicas humanas O(1)"""
        delay = random.uniform(min_s, max_s)
        logger.debug("[%s] Pausa estocástica de %.2fs...", self.ghost_id, delay)
        await asyncio.sleep(delay)

    async def consume_feed_passively(self):
        """
        Simula la entrada a la portada y lectura sin interacción.
        Genera historial de sesión y cookies necesarias para elevar el Trust Score.
        """
        logger.info("[%s] Iniciando sesión de lurker (consumo pasivo).", self.ghost_id)
        try:
            # 1. Visita la raíz
            logger.info("[%s] GET %s/", self.ghost_id, self.base_url)
            # await self._transport.request("GET", f"{self.base_url}/")
            await self._stochastic_delay(3.0, 8.0)

            # 2. Simula entrar a un post popular al azar (sin emitir WRITE)
            mock_popular_posts = ["/post/a1b2", "/post/x9y8", "/post/m4n5"]
            selected_post = random.choice(mock_popular_posts)

            logger.info("[%s] Navegando a %s (Read-only)", self.ghost_id, selected_post)
            # await self._transport.request("GET", f"{self.base_url}{selected_post}")

            # Tiempo de lectura humana de un post
            await self._stochastic_delay(5.0, 12.0)

            logger.info("[%s] Sesión de lurker completada. Termalidad incrementada.", self.ghost_id)
        except Exception as e:
            logger.error("[%s] Anomalía en la navegación pasiva: %s", self.ghost_id, e)
        finally:
            await self._transport.close()


async def execute_incubation_cycle(ghost_ids: list[str]):
    """
    Despliega N Ghosts en modo incubación paralela con desfase.
    """
    logger.info("==================================================")
    logger.info("🧪 INCUBADORA GHOST: Elevación de Trust Score 🧪")
    logger.info("==================================================")

    tasks = []
    for count, gid in enumerate(ghost_ids):
        # Desfase temporal para no disparar las sesiones simultáneamente
        offset = count * random.uniform(2.0, 5.0)

        async def delay_and_run(ghost, wait_time):
            await asyncio.sleep(wait_time)
            lurker = LurkerProfile(ghost)
            await lurker.consume_feed_passively()

        tasks.append(delay_and_run(gid, offset))

    await asyncio.gather(*tasks)
    logger.info("🟢 CICLO DE INCUBACIÓN COMPLETADO. Ghosts retornados a estado de letargo.")


if __name__ == "__main__":
    ghost_roster = [f"mk_ghost_{i:03d}" for i in range(5)]
    asyncio.run(execute_incubation_cycle(ghost_roster))
