import asyncio
import logging
import os
import re
import sys

sys.path.insert(0, os.path.abspath('.'))

from cortex.storage.ledger import EnterpriseAuditLedger
from cortex.engine.autodidact_hott_engine import AutodidactHottEngine
from cortex.engine.ultramap import UltramapSubstrate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("inject_network")

async def inject_primitives():
    logger.info("Iniciando inyección de Primitivas para NETWORK-SOVEREIGNTY...")
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    md_path = "AUTODIDACT_NETWORK.md"
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'-\s*\*\*(NET-\d{3})\*\*:\s*`?([^`]+)`?\s*-\s*(.*)')
    matches = pattern.findall(content)

    if not matches:
        logger.error("No se encontraron primitivas en el archivo markdown.")
        return

    logger.info(f"Se encontraron {len(matches)} primitivas para inyectar.")

    agent_id = 150 # Elevated PID representation for Socket Network Authority
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "NETWORK_ROOT", 0.0)

    for i, match in enumerate(matches):
        p_id, p_name, p_app = [m.strip() for m in match]
        axiom_claim = f"{p_id}: {p_name}"
        constructive_proof = f"Topología P2P sellada a nivel socket: {p_app}. Conectado a la malla oscura."
        
        logger.info(f"Inyectando: {axiom_claim}")
        event_hash = await hott_engine.ingest_axiom(
            agent_idx=agent_id,
            axiom_claim=axiom_claim,
            constructive_proof=constructive_proof
        )
        ultramap.update_agent_position(agent_id, (i + 1) * 1.0, 0.0, 0.0, "DARKNET_NODE", 0.1)
    
    logger.info("Inyección criptográfica de Network Sovereignty completada.")
    await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(inject_primitives())
