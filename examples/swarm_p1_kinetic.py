import asyncio
import logging

from cortex.ledger.core import SovereignLedger
from cortex.services.bounty_service import BountyService
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager

# Configuracion de Logs (Industrial Noir Aesthetic)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cortex.p1.orchestrator")

import sqlite3


async def run_p1_extraction():
    """
    Orquestador de la Escuadra P1 para la extracción masiva de capital y exergía.
    """
    logger.info("--- [Ω] Iniciando Escuadra P1: Extracción de Capital ---")
    
    # 1. Inicializar Infraestructura de Trust (Real, not Mock)
    db_conn = sqlite3.connect(":memory:")
    # Initialize DB Schema for Ledger
    db_conn.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, project TEXT, action TEXT, detail TEXT, prev_hash TEXT, hash TEXT, timestamp TEXT, tenant_id TEXT)")
    db_conn.execute("CREATE TABLE merkle_roots (id INTEGER PRIMARY KEY, root_hash TEXT, tx_start_id INTEGER, tx_end_id INTEGER, tx_count INTEGER)")
    
    ledger = SovereignLedger(db_conn)
    
    from unittest.mock import MagicMock
    router = MagicMock()
    router.default_config = {"model": "gemini-3-pro", "provider": "google"}
    
    manager = SwarmManager(ledger=ledger)
    
    # Registrar skills de soporte para el cuadrante P1
    from pathlib import Path

    from cortex.swarm.discovery import SkillMetadata
    for cat in ["automation", "recruitment", "capital"]:
        skill = SkillMetadata(
            data={"name": f"p1_specialist_{cat}", "category": cat, "version": "1.0"},
            path=Path(f"/tmp/p1_{cat}/SKILL.md")
        )
        manager.registry.skills[skill.name] = skill
        
    factory = SwarmFactory(manager=manager, bus=manager.bus, router=router)
    bounty_service = BountyService(ledger=ledger, reward_threshold=300.0)
    
    # 2. Reclutamiento de la Escuadra P1 (Kinetic Squad) via SwarmCycle (Ω₃)
    logger.info("Iniciando Ciclos de Evolución P1...")
    agent_ids = await factory.recruit_squad(
        objective="Massive capital extraction and automation",
        threshold=0.3, # Umbral de exergía para éxito rápido en demo
        max_cycles=2
    )
    logger.info("Escuadra P1 evolucionada y reclutada: %s", agent_ids)
    
    # 3. Escaneo de Oportunidades (Bounties)
    # Ejemplo con repositorios de alta exergia
    repos = [("google", "cortex"), ("borjamoskv", "Cortex-Persist")]
    all_leads = []
    
    for owner, repo in repos:
        leads = await bounty_service.scan_repository(owner, repo)
        all_leads.extend(leads)
        
    ranked_leads = bounty_service.rank_leads(all_leads)
    
    if not ranked_leads:
        logger.warning("No se encontraron leads de alta exergia. Abortando mision.")
        return

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

    logger.info("--- [\u03a9] Mision de la Escuadra P1 Completada ---")

if __name__ == "__main__":
    asyncio.run(run_p1_extraction())
