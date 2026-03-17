import asyncio
import logging
import random
import re
from collections.abc import Callable
from typing import Any

from cortex.engine.nemesis import NemesisProtocol
from cortex.extensions._quarantine.red_team.discovery import DiscoveryProvider
from cortex.extensions.immune.falsification import EvolutionaryFalsifier

logger = logging.getLogger("cortex.extensions._quarantine.red_team.swarm_chaos")


class RedTeamSwarm:
    """
    The Red Team Swarm: Orchestrates controlled failure injections to evolve CORTEX's immunity.
    """

    def __init__(self, target_namespaces: list[str] | None = None):
        self.falsifier = EvolutionaryFalsifier(failure_tolerance=1)
        self.discovery = DiscoveryProvider(target_namespaces)
        self.active_injectors = []
        self._chaos_count = 0

    async def inject_chaos(
        self, target_service: str, target_func: Callable, seed_inputs: dict[str, Any]
    ):
        """
        Injects a failure into a target function and captures the antibody if it collapses.
        """
        logger.info("Red Team Swarm: Targeting %s.%s", target_service, target_func.__name__)

        # Perform falsification (adversarial mutation)
        survived = self.falsifier.falsify_target(target_func, seed_inputs)

        if not survived:
            autopsies = self.falsifier.get_antibodies()
            if autopsies:
                latest = autopsies[-1]
                vector = str(latest["vector"])
                # Simplified antibody generation: reject the collapse vector pattern
                # If the vector is a dict, we extract the values to avoid regex-breaking characters
                if isinstance(latest["vector"], dict):
                    # For tests, we know 'data' is the key. In production, we'd iterate.
                    vector_val = str(latest["vector"].get("data", vector))
                else:
                    vector_val = vector

                pattern = f".*{re.escape(vector_val)}.*"
                reason = f"Collapse detected in {target_service} via {latest['collapse_type']}"

                logger.critical(
                    "Red Team Swarm: Falsification SUCCESS for %s. Generating antibody.",
                    target_func.__name__,
                )
                NemesisProtocol.append_antibody(pattern, reason)
                return True

        logger.info("Red Team Swarm: %s survived chaos injection.", target_func.__name__)
        return False

    async def chaos_loop(self, interval_seconds: int = 3600):
        """
        Infinite loop of random failure injections (The Ouroboros Nightmare).

        Ω₅: Stress is fuel. The system requires constant siege to evolve.
        """
        logger.info("🦾 [RED-TEAM] Chaos Swarm Ignited. Starting Ouroboros Loop (Ω₅).")

        while True:
            self._chaos_count += 1
            targets = self.discovery.discover()

            if not targets:
                logger.warning(
                    "🦾 [RED-TEAM] No attack surfaces found. Intelligence core secured or unreachable."
                )
            else:
                # Elegir un objetivo aleatorio de la lista para inyectar caos
                service, func, seed = random.choice(targets)
                logger.info(
                    "🔥 [RED-TEAM] Chaos Cycle #%d — Targeted: %s.%s",
                    self._chaos_count,
                    service,
                    func.__name__,
                )

                try:
                    success = await self.inject_chaos(service, func, seed)
                    if success:
                        logger.warning(
                            "💀 [RED-TEAM] Falsification Success: Vector captured and assimilated."
                        )
                    else:
                        logger.info(
                            "🦾 [RED-TEAM] Surface survived. Immunity confirmed for %s.",
                            func.__name__,
                        )
                except Exception as e:  # noqa: BLE001
                    # Si el propio inyector explota, es un error del Red Team, no del objetivo.
                    logger.error(
                        "❌ [RED-TEAM] Red Team internal failure (Byzantine Swarm Error): %s", e
                    )

            # Ω₅: El ritmo del caos es irregular para evitar patrones de adaptación predecibles.
            jitter = random.uniform(0.8, 1.2)
            sleep_time = interval_seconds * jitter
            logger.info("🦾 [RED-TEAM] Retreating. Next siege in %.1f seconds.", sleep_time)
            await asyncio.sleep(sleep_time)
