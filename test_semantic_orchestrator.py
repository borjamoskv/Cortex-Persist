import asyncio
import os
import uuid

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------
from cortex.engine.logic.semantic_crdt import SemanticOrchestrator

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.auth.enterprise_identity import SovereignIdentity


async def test_orchestrator():
    db_path = "/tmp/test_cortex_audit.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    async with aiosqlite.connect(db_path) as conn:
        ledger = EnterpriseAuditLedger(conn)
        
        identity = SovereignIdentity(
            tenant_id="tenant_x",
            actor_id="operator_1",
            role="CRDT_ORCHESTRATOR",
            scopes={"crdt:compact"}
        )
        
        orchestrator = SemanticOrchestrator(
            ledger=ledger,
            identity=identity
        )
        
        print("Inserting 32 supports...")
        for _i in range(32):
            await orchestrator.add_active_support(str(uuid.uuid4()))
            
        print(f"Current active supports count: {len(orchestrator.state.active_supports)}")
        assert len(orchestrator.state.active_supports) == 32
        
        print("Inserting 33rd support (should trigger overflow + compaction)...")
        await orchestrator.add_active_support(str(uuid.uuid4()))
        
        print(f"Post-overflow active supports count: {len(orchestrator.state.active_supports)}")
        assert len(orchestrator.state.active_supports) == 1
        
        # Verify the ledger was written to
        async with conn.execute("SELECT audit_id, action, resource FROM security_audit_log WHERE action='CRDT_COMPACT'") as cursor:
            rows = await cursor.fetchall()
            print(f"Compaction events in ledger: {len(rows)}")
            assert len(rows) == 1
            print(f"Resource logged: {rows[0][2][:50]}...")
            
        print("All tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
