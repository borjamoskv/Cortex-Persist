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
logger = logging.getLogger("inject_moskv1_apex_capabilities")

async def inject_primitives():
    logger.info("Iniciando inyección de 50 Primitivas MOSKV-1 APEX Capabilities...")
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)

    md_path = "AUTODIDACT_MOSKV1_APEX_CAPABILITIES.md"
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'-\s*\*\*(APEX-\d{3})\*\*:\s*`?([^`]+)`?\s*-\s*(.*)')
    matches = pattern.findall(content)

    logger.info(f"Primitivas detectadas: {len(matches)}")

    agent_id = 99
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "MOSKV1_APEX_ROOT", 0.0)

    success_count = 0
    fail_count = 0

    for i, match in enumerate(matches):
        p_id, p_name, p_app = [m.strip() for m in match]
        axiom_claim = f"{p_id}: {p_name}"
        constructive_proof = f"Aplicación estructural en C5-REAL: {p_app}. DAG vinculado por HoTT engine. Sello: borjamoskv."

        try:
            event_hash = await hott_engine.ingest_axiom(
                agent_idx=agent_id,
                axiom_claim=axiom_claim,
                constructive_proof=constructive_proof
            )
            logger.info(f"[{i+1:02d}/50] {p_id} → Hash: {event_hash[:16]}...")
            ultramap.update_agent_position(agent_id, (i + 1) * 1.0, 0.0, 0.0, "MOSKV1_APEX_LEAF", 0.1)
            success_count += 1
        except Exception as e:
            logger.error(f"[{i+1:02d}/50] {p_id} FAILED: {e}")
            fail_count += 1

    logger.info(f"Inyección completada. Éxito: {success_count} | Fallos: {fail_count}")
    await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(inject_primitives())
