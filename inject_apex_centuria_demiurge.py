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
logger = logging.getLogger("inject_apex_centuria_phase6_7")

async def inject_primitives():
    logger.info("Inyección selectiva: APEX-051→100 (Fases 6 y 7 del Demiurgo)...")
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)

    md_path = "AUTODIDACT_MOSKV1_APEX_CAPABILITIES.md"
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'-\s*\*\*(APEX-\d{3})\*\*:\s*`?([^`\n]+?)`?\s*-\s*(.*)')
    matches = pattern.findall(content)

    # Filter only APEX-051 through APEX-100
    new_matches = [(pid, pname, papp) for pid, pname, papp in matches if int(pid.split('-')[1]) >= 51]
    logger.info(f"Primitivas nuevas detectadas: {len(new_matches)}")

    agent_id = 100  # Demiurge agent slot
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "DEMIURGE_CENTURIA_ROOT", 0.0)

    success_count = 0
    fail_count = 0

    for i, (p_id, p_name, p_app) in enumerate(new_matches):
        p_id, p_name, p_app = p_id.strip(), p_name.strip(), p_app.strip()
        axiom_claim = f"{p_id}: {p_name}"
        constructive_proof = f"Fase {'6' if int(p_id.split('-')[1]) <= 75 else '7'} C5-REAL: {p_app}. Inyectado por el Demiurgo (borjamoskv). DAG HoTT vinculado."

        try:
            event_hash = await hott_engine.ingest_axiom(
                agent_idx=agent_id,
                axiom_claim=axiom_claim,
                constructive_proof=constructive_proof
            )
            logger.info(f"[{i+1:02d}/{len(new_matches)}] {p_id} → Hash: {event_hash[:16]}...")
            ultramap.update_agent_position(agent_id, (i + 1) * 1.0, 0.0, 0.0, "DEMIURGE_CENTURIA_LEAF", 0.1)
            success_count += 1
        except Exception as e:
            logger.error(f"[{i+1:02d}/{len(new_matches)}] {p_id} FAILED: {e}")
            fail_count += 1

    logger.info(f"Inyección Demiurgo completada. Éxito: {success_count} | Fallos: {fail_count}")
    await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(inject_primitives())
