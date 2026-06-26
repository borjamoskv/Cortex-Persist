import pytest
pytestmark = pytest.mark.chaos
import sqlite3
import aiosqlite
import hashlib
from cortex.database.core import connect, connect_async
from cortex.audit.ledger import EnterpriseAuditLedger

# [Level 20: Physical Claims Audit - Storage Boundary]
# Destructive tests to measure Causal Surface Area at the DB level

@pytest.fixture
def test_db_path(tmp_path):
    return str(tmp_path / "test_cortex_metal.db")

def test_ataque_b_sql_direct(test_db_path):
    """
    Test Attack B: Direct SQL injection
    Attempting to bypass CortexConnection and/or causal authorizer.
    """
    # 1. Bypass factory entirely (cortex.database.core patches sqlite3.connect)
    with pytest.raises(RuntimeError, match=r"Direct sqlite3.connect\(\) is structurally forbidden"):
        sqlite3.connect(test_db_path)

    # 2. Use the factory but without causal authorization
    conn = connect(test_db_path)
    
    # CREATE TABLE is DDL, which might pass if not explicitly denied.
    # The authorizer in CortexConnection denies INSERT, UPDATE, DELETE if not authorized.
    conn.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT)")
    
    with pytest.raises(sqlite3.DatabaseError, match=r"not authorized"):
        # The authorizer denies INSERT because causal_write_authorized is False
        conn.execute("INSERT INTO memory (id) VALUES ('fake')")

@pytest.mark.asyncio
async def test_ataque_c_wal_injection(test_db_path):
    """
    Test Attack C: WAL Injection / Storage Mutation
    Attempting to alter the storage after validation, 
    and verify if the ledger detects it.
    """
    # Create valid ledger entries
    conn = await connect_async(test_db_path)
    
    # Authorize writes for the setup phase
    conn._conn.authorize_causal_writes()
    
    ledger = EnterpriseAuditLedger(conn)
    await ledger.ensure_table()
    
    # 1 validate and persist
    await ledger.log_action("tenant1", "admin", "agent1", "STORE", "resource1")
    await ledger.log_action("tenant1", "admin", "agent2", "STORE", "resource2")
    
    # Force batch worker to flush if needed
    # (Since it's async and batched, we might need to wait for the task to finish)
    if ledger._batch_task and not ledger._batch_task.done():
        await ledger._batch_task
    
    # Check chain is verified
    res = await ledger.verify_chain()
    assert res["status"] == "verified", f"Chain initially broken: {res}"

    # 3 mutate storage directly (simulating disk/WAL injection)
    # We alter the actor_id of the first record without updating signature
    await conn.execute("UPDATE security_audit_log SET actor_id = 'hacker' WHERE resource = 'resource1'")
    await conn.commit()
    
    # 4 replay / verify chain
    res_tampered = await ledger.verify_chain()
    assert res_tampered["status"] == "tampered"
    assert res_tampered["reason"] == "row_hash_mismatch"
    
    await conn.close()
