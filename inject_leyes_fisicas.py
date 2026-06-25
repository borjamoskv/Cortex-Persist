# Creator/Autor: Borja Moskv (borjamoskv)
# Protocolo: C5-REAL | Inyección de Primitivas de Leyes Físicas

import asyncio
import logging
import os
import re
import sys

sys.path.insert(0, os.path.abspath('.'))

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.autodidact_hott_engine import AutodidactHottEngine
from cortex.engine.ultramap import UltramapSubstrate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("inject_leyes_fisicas")

async def inject_primitives():
    logger.info("Iniciando inyección de Primitivas LEYES FÍSICAS en CORTEX-Persist (C5-REAL)...")
    
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    md_path = "AUTODIDACT_LEYES_FISICAS.md"
    if not os.path.exists(md_path):
        logger.error(f"Falta el manifiesto: {md_path}")
        return

    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    # Extraer ID, Primitiva, Aplicación
    pattern = re.compile(r'-\s*\*\*(LEYES-FISICAS-\d{3})\*\*:\s*`?([^`\n]+?)`?\s*-\s*(.*)')
    matches = pattern.findall(content)

    if not matches:
        logger.warning("No se encontraron primitivas para inyectar.")
        return

    agent_id = 99  # Agent ID reservado para LEYES-FISICAS INJECTOR
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "LEYES_FISICAS_ROOT", 0.0)

    injected_count = 0
    for match in matches:
        p_id = match[0].strip()
        p_name = match[1].strip()
        p_app = match[2].strip()
        
        axiom_claim = f"{p_id}: {p_name}"
        constructive_proof = f"Aplicación estructural en C5-REAL: {p_app}. DAG vinculado por HoTT engine."
        
        try:
            event_hash = await hott_engine.ingest_axiom(
                agent_idx=agent_id,
                axiom_claim=axiom_claim,
                constructive_proof=constructive_proof
            )
            logger.info(f"[{p_id}] Cristalizado en O(1) -> Hash: {event_hash}")
            injected_count += 1
            
            ultramap.update_agent_position(agent_id, injected_count * 1.0, 0.0, 0.0, "LEYES_FISICAS_LEAF", 0.1)
        except Exception as e:
            logger.error(f"Fallo termodinámico en {p_id}: {e}")

    logger.info(f"Inyección completada: {injected_count}/{len(matches)} primitivas insertadas con éxito.")
    # Allow background ledger batch writer to flush to disk
    await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(inject_primitives())
