import asyncio
import logging
import os
import re
import sys

sys.path.insert(0, os.path.abspath('.'))

from babylon60.audit.ledger import EnterpriseAuditLedger

import cortex_rs
from babylon60.database.core import connect_async

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("inject_educational")

async def inject_primitives():
    logger.info("Iniciando inyección Ultramap de Primitivas Educativas...")
    try:
        ultramap = cortex_rs.UltramapSubstrate("ultramap.bin", capacity=10000)
    except AttributeError:
        class MockUltramap:
            def update_agent_position(self, *args, **kwargs): pass
        ultramap = MockUltramap()
        logger.warning("C5-REAL Ultramap backend not available. Using MockUltramap.")
        
    md_path = "AUTODIDACT_EDUCATIONAL_PRIMITIVES.md"
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    # Pattern matches: - **EDU-001**: `Adaptive Learning (EDG)` - Grafo de Dependencias Epistémicas...
    pattern = re.compile(r'-\s*\*\*(EDU-\d{3})\*\*:\s*`?([^`]+)`?\s*-\s*(.*)')
    matches = pattern.findall(content)

    if not matches:
        logger.error("No se encontraron primitivas (EDU-XXX) en el manifiesto.")
        return

    agent_id = 101 # Unique ID for educational context
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "EDU_ROOT", 0.0)

    db_path = os.getenv("CORTEX_DB_PATH", "cortex_reality.db")
    async with connect_async(db_path) as conn:
        ledger = EnterpriseAuditLedger(conn=conn)
        await ledger.ensure_table()

        for i, match in enumerate(matches):
            p_id, p_name, p_app = [m.strip() for m in match]
            axiom_claim = f"{p_id}: {p_name}"
            
            event_hash = await ledger.log_action(
                tenant_id="system",
                actor_role="autodidact",
                actor_id=str(agent_id),
                action="inject_axiom",
                resource=axiom_claim
            )
            logger.info(f"Ingested {p_id} -> Hash: {event_hash}")
            ultramap.update_agent_position(agent_id, (i + 1) * 1.0, 0.0, 0.0, "EDU_LEAF", 0.1)
        
        await asyncio.sleep(1.0)
    logger.info("Inyección holográfica completada exitosamente.")

if __name__ == "__main__":
    asyncio.run(inject_primitives())
