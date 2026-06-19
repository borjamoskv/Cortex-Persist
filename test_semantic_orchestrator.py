import asyncio
import aiosqlite
import os
import uuid
from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.logic.semantic_crdt import SemanticOrchestrator

async def test_orchestrator():
    db_path = "/tmp/test_cortex_audit.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    async with aiosqlite.connect(db_path) as conn:
        ledger = EnterpriseAuditLedger(conn)
        # We need to start the background worker or it might lock up?
        # The EnterpriseAuditLedger creates a task using asyncio.get_running_loop()
        
        orchestrator = SemanticOrchestrator(
            ledger=ledger,
            tenant_id="tenant_x",
            actor_id="operator_1"
        )
        
        print("Inserting 32 supports...")
        for i in range(32):
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
