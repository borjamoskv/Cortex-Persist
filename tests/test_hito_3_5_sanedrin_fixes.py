# [C5-REAL] Exergy-Maximized
import asyncio
import uuid
import pytest
import aiosqlite
from datetime import datetime, timezone

from cortex.engine.swarm.supervisor import SwarmSupervisor, DummyAgent
from cortex.engine.swarm.legion import SwarmSignal
from cortex.engine.swarm.state_store import CausalStateStore

async def setup_db(db_path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    await db.execute("PRAGMA journal_mode=WAL;")
    
    await db.execute('''
        CREATE TABLE IF NOT EXISTS system_hypotheses (
            id TEXT PRIMARY KEY,
            statement TEXT,
            probability REAL,
            evi REAL,
            cost REAL,
            impact REAL,
            status TEXT,
            created_at TEXT,
            owner_id TEXT
        )
    ''')
    await db.execute('''
        CREATE TABLE IF NOT EXISTS cortex_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    await db.execute("INSERT INTO cortex_meta (key, value) VALUES ('hypothesis_graph_version', '1')")
    await db.commit()
    return db

@pytest.fixture(autouse=True)
def mock_causal_guard(monkeypatch):
    class MockGuard:
        def verify_closure(self, proposal):
            pass
    import cortex.engine.swarm.state_store
    monkeypatch.setattr(cortex.engine.swarm.state_store, "CausalClosureGuard", MockGuard)

@pytest.mark.asyncio
async def test_2pc_atomic_commit():
    """Test SAGA 2PC: If state mutation fails, Ledger event is rolled back."""
    db_path = f"/tmp/supervisor_test_2pc_{uuid.uuid4().hex}.db"
    db = await setup_db(db_path)
    
    # Insert 1 task
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO system_hypotheses (id, statement, probability, evi, cost, impact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("hyp-test-2pc", "Stmt", 1.0, 1.0, 1.0, 1.0, 'ACTIVE', now)
    )
    await db.commit()
    await db.close()

    store = CausalStateStore(db_path=db_path)
    await store.connect()
    
    # We will mock the database commit to fail to trigger the rollback logic
    original_commit = store._db.commit
    async def mock_commit():
        raise RuntimeError("I/O Failure Simulated")
    
    store._db.commit = mock_commit

    signal = SwarmSignal(
        agent_id="agent-001",
        target="hyp-test-2pc",
        status="SUCCESS",
        payload={"data": "test"},
        metrics={}
    )
    
    # Process signal should swallow the exception but rollback
    await store.process_signal(signal)
    
    # Restore commit just in case
    store._db.commit = original_commit
    
    # Verify rollback
    verify_db = await aiosqlite.connect(db_path)
    
    # 1. Hypothesis status should still be ACTIVE
    async with verify_db.execute("SELECT status FROM system_hypotheses WHERE id = 'hyp-test-2pc'") as cur:
        status = (await cur.fetchone())[0]
        assert status == "ACTIVE", "State mutation was not rolled back"
        
    # 2. Audit Ledger should be EMPTY (rolled back)
    async with verify_db.execute("SELECT count(*) FROM audit_ledger") as cur:
        ledger_count = (await cur.fetchone())[0]
        assert ledger_count == 0, "Ledger event was not rolled back (SPLIT BRAIN DETECTED)"

    await verify_db.close()
    await store.close()

@pytest.mark.asyncio
async def test_lease_locks_and_ghost_recovery():
    """Test SANEDRIN VECTOR 3: Lease locks and IN_FLIGHT recovery"""
    db_path = f"/tmp/supervisor_test_lease_{uuid.uuid4().hex}.db"
    db = await setup_db(db_path)
    
    # Insert 1 IN_FLIGHT task belonging to an old supervisor
    now = datetime.now(timezone.utc).isoformat()
    old_lease = "OLD_LEASE_123"
    await db.execute(
        "INSERT INTO system_hypotheses (id, statement, probability, evi, cost, impact, status, created_at, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("hyp-test-lease", "Stmt", 1.0, 1.0, 1.0, 1.0, 'IN_FLIGHT', now, old_lease)
    )
    await db.commit()
    await db.close()

    # Supervisor 1 starts and does global sweep
    supervisor = SwarmSupervisor(db_path=db_path)
    await supervisor.initialize()
    
    # Verify task was recovered to ACTIVE
    verify_db = await aiosqlite.connect(db_path)
    async with verify_db.execute("SELECT status, owner_id FROM system_hypotheses WHERE id = 'hyp-test-lease'") as cur:
        row = await cur.fetchone()
        assert row[0] == "ACTIVE"
        assert row[1] == old_lease  # Owner id remains but status is ACTIVE
        
    # Now Supervisor dispatch it, it should acquire new lease
    await supervisor.dispatch_optimal_hypotheses(1)
    
    async with verify_db.execute("SELECT status, owner_id FROM system_hypotheses WHERE id = 'hyp-test-lease'") as cur:
        row = await cur.fetchone()
        assert row[0] == "IN_FLIGHT"
        assert row[1] == supervisor.supervisor_id  # New lease acquired
        
    await supervisor.shutdown()
    await verify_db.close()
