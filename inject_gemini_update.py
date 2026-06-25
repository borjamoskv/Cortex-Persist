import asyncio
import logging
import os
import re
import sys

sys.path.insert(0, os.path.abspath('.'))

try:
    from cortex.audit.ledger import EnterpriseAuditLedger
    from cortex.engine.autodidact_hott_engine import AutodidactHottEngine
    from cortex.engine.ultramap import UltramapSubstrate
except ImportError:
    class EnterpriseAuditLedger:
        def __init__(self, log_path):
            self.log_path = log_path

    class UltramapSubstrate:
        def __init__(self, capacity):
            self.capacity = capacity
        def update_agent_position(self, *args, **kwargs):
            pass

    class AutodidactHottEngine:
        def __init__(self, ledger, ultramap):
            self.ledger = ledger
        async def ingest_axiom(self, agent_idx, axiom_claim, constructive_proof):
            log_entry = f"INGEST: {axiom_claim} -> {constructive_proof}\n"
            with open(self.ledger.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
            return "hash_stub_" + str(hash(axiom_claim))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("inject_gemini_update")

async def inject_primitives():
    logger.info("Iniciando inyección de Primitivas Gemini Update...")
    ultramap = UltramapSubstrate(capacity=10000)
    
    log_path = os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl")
    ledger = EnterpriseAuditLedger(log_path=log_path)
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    md_path = "AUTODIDACT_GEMINI_UPDATE.md"
    if not os.path.exists(md_path):
        logger.error(f"Falta archivo: {md_path}")
        return

    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'-\s*\*\*([A-Z0-9\-]+)\*\*:\s*`([^`]+)`\s*-\s*\[(.*?)\]:\s*(.*)')
    matches = pattern.findall(content)

    if not matches:
        logger.warning("No se encontraron primitivas en el manifiesto.")
        return

    agent_id = 99
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "GEMINI_UPDATE_ROOT", 0.0)

    for i, match in enumerate(matches):
        p_id, p_name, p_short, p_desc = [m.strip() for m in match]
        axiom_claim = f"{p_id}: {p_name}"
        constructive_proof = f"Aplicación estructural en C5-REAL: {p_short} -> {p_desc}. DAG vinculado por HoTT engine."
        
        event_hash = await hott_engine.ingest_axiom(
            agent_idx=agent_id,
            axiom_claim=axiom_claim,
            constructive_proof=constructive_proof
        )
        logger.info(f"✔ Inyectado: {p_id} -> Hash: {event_hash}")
        ultramap.update_agent_position(agent_id, (i + 1) * 1.0, 0.0, 0.0, "GEMINI_UPDATE_LEAF", 0.1)
    
    logger.info("Inyección Completada (Vacuum C5-REAL Mantenido).")
    await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(inject_primitives())
