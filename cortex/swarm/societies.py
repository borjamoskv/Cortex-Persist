"""
cortex/swarm/societies.py
─────────────────────────
Sovereign Swarm Societies / Syndicates Architecture

Permite la orquestación de agentes no como "nodos aislados", sino como
"Sociedades" o Facciones estructurales. Cientos de agentes pueden unirse para
formar una Sociedad, compartiendo Exergy (`budget`), intercambiando inteligencia
vía el `AsyncSignalBus`, o ejecutando ataques coordinados masivos (Swarm Strikes).

Axioma Táctico: Individual agents fail. Syndicates compound.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from cortex.swarm.bus import SwarmSignal
from cortex.swarm.manager import SwarmManager

logger = logging.getLogger("cortex.swarm.societies")


@dataclass
class SwarmSociety:
    """
    Una corporación soberana o facción formada por múltiples agentes.
    """
    name: str
    members: set[str] = field(default_factory=set)
    exergy_pool: float = 0.0  # Pooled resources/budget
    doctrine: str = "P1 Kinetic Dominance"
    society_id: str = field(default_factory=lambda: f"soc-{uuid.uuid4().hex[:8]}")

    def add_member(self, agent_id: str) -> None:
        self.members.add(agent_id)
        logger.info("[Society %s] Member %s assimilated.", self.name, agent_id)

    def remove_member(self, agent_id: str) -> None:
        self.members.discard(agent_id)

    def is_solvent(self, required_exergy: float) -> bool:
        return self.exergy_pool >= required_exergy

    def exact_tribute(self, amount: float) -> None:
        """Deduce exergy from the collective pool to fund an operation."""
        self.exergy_pool -= amount


class SocietyManager:
    """
    Rige las interacciones entre diversas Sociedades Soberanas en CORTEX.
    Permite el alineamiento ("Alliance") o el asedio ("Siege") de Facciones.
    """
    def __init__(self, swarm_manager: SwarmManager | None = None):
        self.orchestrator = swarm_manager or SwarmManager()
        self.societies: dict[str, SwarmSociety] = {}

    def form_society(self, name: str, doctrine: str) -> SwarmSociety:
        """Funda una nueva facción dentro del Swarm."""
        soc = SwarmSociety(name=name, doctrine=doctrine)
        self.societies[soc.society_id] = soc
        logger.info("SocietyManager: 🏛️ Society '%s' forged under doctrine '%s'.", name, doctrine)
        return soc

    def disband_society(self, society_id: str) -> None:
        """Disuelve la facción."""
        if society_id in self.societies:
            del self.societies[society_id]
            logger.info("SocietyManager: 💥 Society %s disbanded.", society_id)

    async def collective_strike(self, society_id: str, target: str, payload_task: str) -> list[Any]:
        """
        Ejecuta un ataque coordinado fondeado y ejecutado masivamente por la Sociedad completa.
        Sólo si la Sociedad es solvente y tiene quorum participativo.
        """
        if society_id not in self.societies:
            raise ValueError(f"Society {society_id} does not exist.")

        soc = self.societies[society_id]

        # Require minimal exergy for a collective deployment
        cost_per_agent = 1.0
        total_deployment_cost = len(soc.members) * cost_per_agent

        if not soc.is_solvent(total_deployment_cost):
            logger.warning("[Society %s] Bankruptcy threshold. Cannot afford collective strike.", soc.name)
            return []

        logger.info("[Society %s] Declaring strike on '%s'. Committing %d agents.", soc.name, target, len(soc.members))
        soc.exact_tribute(total_deployment_cost)

        # Parallel Multi-Agent execution via Sharding
        # Deploy specific society members instead of an arbitrary squad count
        responses = await self.orchestrator.shard_task(
            agent_ids=list(soc.members),
            task=f"Society Directive [{soc.doctrine}]: Strike target {target} with payload {payload_task}"
        )

        # Broadcast the impact via Signal Bush
        strike_signal = SwarmSignal(
            sender=f"society_{soc.name}",
            topic="SOCIETY_STRIKE_RESULT",
            payload={"target": target, "yield": len(responses)}
        )
        await self.orchestrator.bus.publish(strike_signal)

        return responses


async def __test_societies():
    """Prueba interactiva del módulo de sociedades."""
    logging.basicConfig(level=logging.INFO)
    mgr = SocietyManager()

    # 1. Forge the "Data Cartel" society
    cartel = mgr.form_society("The Data Cartel", doctrine="Vector J Synthesis Mimetics")

    # 2. Assimilate IP Forge agents
    for i in range(10):
        cartel.add_member(f"ip-forge-{i}")

    # 3. Fund the cartel
    cartel.exergy_pool = 150.0  # USD / Tokens

    # 4. Announce a collective strike on Gumroad
    await mgr.collective_strike(cartel.society_id, target="Gumroad Ecosystem", payload_task="Synthesize API Endpoints")

if __name__ == "__main__":
    asyncio.run(__test_societies())
