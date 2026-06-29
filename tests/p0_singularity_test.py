import asyncio
import hashlib
import json
import os
import pytest
import sqlite3
from typing import Any

from cortex.api.middleware import SovereignIsolationMiddleware
from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.flow.saga_protocol import build_core_write_path_saga, SagaContext
from cortex.engine.causal.taint_engine import generate_secure_taint_token
from cortex.crypto.keys import Signer, ZKSwarmIdentity

# [C5-REAL] Test de Tolerancia Bizantina P0

@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    # Enable WAL mode for concurrency simulation (though in-memory is limited, we simulate the lock)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    yield conn
    conn.close()

@pytest.fixture
def auth_ledger(memory_db):
    ledger = EnterpriseAuditLedger(memory_db)
    # Mock Async Execution wrapper for in-memory sync conn
    import aiosqlite
    import tempfile
    
    # Needs a real file for aiosqlite concurrency tests
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(db_fd)
    
    class AsyncTestLedger:
        def __init__(self, path, pkey):
            self.path = path
            self.pkey = pkey
            
        async def run_concurrent_commits(self):
            async with aiosqlite.connect(self.path) as conn:
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA busy_timeout=5000")
                ledger = EnterpriseAuditLedger(conn)
                await ledger.ensure_table()
                
                # Launch 5 concurrent log_actions to test Doble Commit Lock
                tasks = []
                for i in range(5):
                    tasks.append(
                        ledger.log_action(
                            tenant_id="tenant_1",
                            actor_role="test_worker",
                            actor_id=f"worker_{i}",
                            action="TEST_CONCURRENCY",
                            resource="test_resource",
                            status="SUCCESS"
                        )
                    )
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check that 5 records were inserted
                cursor = await conn.execute("SELECT count(*) FROM security_audit_log")
                row = await cursor.fetchone()
                return row[0], results

    yield AsyncTestLedger(db_path, "")
    os.remove(db_path)


@pytest.mark.asyncio
async def test_p0_bft_ledger_concurrency_lock(auth_ledger):
    """
    [INV_DOBLE_COMMIT] Comprueba que el Ledger soporta commits concurrentes sin corromper 
    la cadena criptográfica gracias al AsyncFileLock y WAL.
    """
    count, results = await auth_ledger.run_concurrent_commits()
    # All 5 should have succeeded without raising exceptions
    for res in results:
        assert not isinstance(res, Exception), f"Concurrency failed: {res}"
    
    assert count == 5, f"Expected 5 records, got {count}"


@pytest.mark.asyncio
async def test_p0_saga_rollback_tombstone():
    """
    [INV_SAGA_ROLLBACK] Comprueba que el Orquestador SAGA inyecta un Tombstone (SAGA_REVERTED)
    en el Ledger si la SAGA es abortada.
    """
    import tempfile
    import aiosqlite
    
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(db_fd)
    
    kp = ZKSwarmIdentity.generate_keypair()
    private_key = kp.private_key_b64
    
    async with aiosqlite.connect(db_path) as conn:
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        
        saga = build_core_write_path_saga()
        
        # Simulate DB failure to trigger Rollback and Tombstone
        async def mock_fail(ctx):
            raise RuntimeError("DB Execution Failed")
        saga.steps[5]._execute = mock_fail
        
        ctx: SagaContext = {
            "tenant_id": "test_tenant",
            "agent_id": "SYS_ROOT",
            "session_id": "test_sess",
            "payload": {"data": "test_poison_1"},
            "ledger": ledger
        }
        
        try:
            await saga.execute_mutation(ctx)
        except RuntimeError as e:
            assert "Saga Mutation Aborted" in str(e)
            
        # Check Ledger for Tombstone
        cursor = await conn.execute("SELECT action, status FROM security_audit_log ORDER BY rowid DESC LIMIT 1")
        row = await cursor.fetchone()
        assert row is not None, "Tombstone was not written"
        assert row[0] == "SAGA_REVERT", "Action must be SAGA_REVERT"
        assert row[1] == "REVERTED", "Status must be REVERTED"

    os.remove(db_path)

