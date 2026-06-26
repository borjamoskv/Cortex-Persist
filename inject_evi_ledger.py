import asyncio
import logging
import os
import re
import sys

import aiosqlite

sys.path.insert(0, os.path.abspath('.'))

import cortex_rs
from cortex.audit.ledger import EnterpriseAuditLedger

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("inject_evi_ledger")

async def inject_primitives():
    logger.info("Iniciando inyección Ultramap de Primitivas EVI/Ledger...")
    try:
        ultramap = cortex_rs.UltramapSubstrate("ultramap.bin", capacity=10000)
    except AttributeError:
        class MockUltramap:
            def update_agent_position(self, *args, **kwargs): pass
        ultramap = MockUltramap()
        logger.warning("C5-REAL Ultramap backend not available. Using MockUltramap.")
        
    md_path = "AUTODIDACT_EVI_LEDGER.md"
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'-\s*\*\*(EVI-\d{3})\*\*:\s*`?([^`]+)`?\s*-\s*(.*)')
    matches = pattern.findall(content)

    if not matches:
        logger.error("No se encontraron primitivas (EVI-XXX) en el manifiesto.")
        return

    agent_id = 102 # Unique ID for EVI context
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "EVI_ROOT", 0.0)

    db_path = os.getenv("CORTEX_DB_PATH", "cortex_reality.db")
    
    # We must use the factory pattern since the database has the CortexConnection guard
    from cortex.database.core import CortexConnection
    
    async with aiosqlite.connect(db_path, factory=CortexConnection) as conn:
        # Since we are writing to the audit ledger, we MUST explicitly authorize causal writes
        if hasattr(conn._conn, "authorize_causal_writes"):
            conn._conn.authorize_causal_writes()
            
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
            ultramap.update_agent_position(agent_id, (i + 1) * 1.0, 0.0, 0.0, "EVI_LEAF", 0.1)
            
        if hasattr(conn._conn, "revoke_causal_writes"):
            conn._conn.revoke_causal_writes()
        
        await asyncio.sleep(1.0)
    logger.info("Inyección holográfica completada exitosamente.")

if __name__ == "__main__":
    asyncio.run(inject_primitives())
