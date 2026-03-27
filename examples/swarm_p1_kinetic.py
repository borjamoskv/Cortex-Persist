import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiosqlite

from cortex.ledger.core import SovereignLedger
from cortex.services.bounty_service import BountyService
from cortex.swarm.discovery import SkillMetadata
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager

# Configuracion de Logs (Industrial Noir Aesthetic)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cortex.p1.orchestrator")


async def run_p1_extraction():
    """
    Orquestador de la Escuadra P1 para la extracción masiva de capital y exergía.
    """
    logger.info("--- [Ω] Iniciando Escuadra P1: Extracción de Capital ---")

    # 1. Inicializar Infraestructura de Trust (Async)
    async with aiosqlite.connect(":memory:") as db_conn:
        ledger = SovereignLedger(db_conn)
        await ledger.ensure_schema()

        router = AsyncMock()
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_result.unwrap.return_value = "Mocked LLM Response for Bounty"
        router.execute_resilient.return_value = mock_result
        router.default_config = {"model": "gemini-3-pro", "provider": "google"}

        manager = SwarmManager(ledger=ledger)

        # Registrar skills de soporte para el cuadrante P1
        for cat in ["automation", "recruitment", "capital"]:
            skill = SkillMetadata(
                data={"name": f"p1_specialist_{cat}", "category": cat, "version": "1.0"},
                path=Path(f"/tmp/p1_{cat}/SKILL.md")
            )
            manager.registry.skills[skill.name] = skill

        factory = SwarmFactory(manager=manager, router=router)
        bounty_service = BountyService(ledger=ledger, reward_threshold=5.0)

        # 2. Reclutamiento de la Escuadra P1 (Kinetic Squad) via SwarmCycle (Ω₃)
        logger.info("Iniciando Ciclos de Evolución P1...")
        agent_ids = await factory.recruit_squad(
            quadrant="P1",
            size=3
        )
        logger.info("Escuadra P1 evolucionada y reclutada: %s", agent_ids)

        # 3. Escaneo de Oportunidades (Bounties)
        # Mocking scan for the demo
        repos = [("google", "cortex"), ("borjamoskv", "Cortex-Persist")]
        all_leads = []
        
        for owner, repo in repos:
            leads = await bounty_service.scan_repository(owner, repo)
            all_leads.extend(leads)

        ranked_leads = await bounty_service.rank_leads(all_leads)

        if not ranked_leads:
            logger.warning("No se encontraron leads de alta exergia. Usando leads simulados.")
            from cortex.services.bounty_service import BountyLead
            ranked_leads = [BountyLead(
                number=1,
                title="Critical Path Optimization (Ω₁₃ Path)",
                url="https://github.com/google/cortex/issues/1",
                reward_usd=500.0,
                difficulty="high",
                score=10.0,
                repo="google/cortex"
            )]

        # 4. Distribucion de Tareas (Sharding)
        target_lead = ranked_leads[0]
        task_description = bounty_service.generate_claim_prompt(target_lead)

        logger.info("Distribuyendo tarea a la Escuadra P1: %s", task_description)

        # Ejecucion paralela via SwarmManager.shard_task (CORTEX-100)
        responses = await manager.shard_task(agent_ids, task_description)

        for i, resp in enumerate(responses):
            status = resp.get("status", "unknown")
            tx_hash = resp.get("metadata", {}).get("cortex_tx_hash", "no_tx")
            logger.info("Agente %s | Status: %s | Tx: %s", agent_ids[i], status, tx_hash)

        logger.info("--- [Ω] Mision de la Escuadra P1 Completada ---")

if __name__ == "__main__":
    asyncio.run(run_p1_extraction())
