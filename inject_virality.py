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
logger = logging.getLogger("inject_virality")

async def inject_primitives():
    logger.info("Iniciando inyección de Primitivas Virales...")
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    md_path = "AUTODIDACT_VIRALITY.md"
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'-\s*\*\*(VRL-\d{3})\*\*:\s*`?([^`\n]+?)`?\s*-\s*(.*)')
    matches = pattern.findall(content)

    agent_id = 99
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "VIRALITY_ROOT", 0.0)

    for i, match in enumerate(matches):
        p_id, p_name, p_app = [m.strip() for m in match]
        axiom_claim = f"{p_id}: {p_name}"
        constructive_proof = f"Aplicación estructural en C5-REAL: {p_app}. DAG vinculado por HoTT engine."
        
        event_hash = await hott_engine.ingest_axiom(
            agent_idx=agent_id,
            axiom_claim=axiom_claim,
            constructive_proof=constructive_proof
        )
        ultramap.update_agent_position(agent_id, (i + 1) * 1.0, 0.0, 0.0, "VIRALITY_LEAF", 0.1)
    
    await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(inject_primitives())
