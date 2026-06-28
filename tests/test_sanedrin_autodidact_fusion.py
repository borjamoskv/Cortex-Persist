import asyncio
import json
import pytest
from cortex.swarm.supervisor import SwarmSupervisor
from cortex.database.core import connect_async, causal_write
from cortex.config import DB_PATH

@pytest.mark.asyncio
async def test_epistemic_breaker_rejects_narrative(tmp_path):
    """
    Sanedrin-Autodidact Fusion test:
    Verify that SwarmSupervisor rejects non-Epistemological tasks.
    """
    db_path = str(tmp_path / "cortex_test.db")
    
    # Create dummy schema first
    # Create dummy schema first
    db = await connect_async(db_path)
    try:
        with causal_write(db):
            await db.execute('''
                CREATE TABLE IF NOT EXISTS system_hypotheses (
                    id TEXT PRIMARY KEY,
                    payload TEXT,
                    status TEXT,
                    priority INTEGER,
                    owner_id TEXT,
                    lease_expires_at TEXT
                )
            ''')
            # 1. Inject Stochastic Slop (Narrative)
            await db.execute(
                "INSERT INTO system_hypotheses (id, payload, status, priority) VALUES (?, ?, ?, ?)",
                ("hyp-slop", json.dumps({"content": "This is a hallucinated LLM plan without latent basis"}), "ACTIVE", 10)
            )
            # 2. Inject valid Hypothesis
            valid_hypothesis = {
                "latent_basis": {
                    "inputs": [],
                    "model": "rule_based",
                    "posterior": 0.99,
                    "inferred_state": {}
                },
                "proposed_intervention": {
                    "action_name": "test_action",
                    "parameters": {},
                    "predicted_outcomes": {},
                    "confidence": 0.9
                }
            }
            await db.execute(
                "INSERT INTO system_hypotheses (id, payload, status, priority) VALUES (?, ?, ?, ?)",
                ("hyp-valid", json.dumps(valid_hypothesis), "ACTIVE", 10)
            )
            await db.execute(
                "CREATE TABLE IF NOT EXISTS cortex_meta (key TEXT PRIMARY KEY, value TEXT)"
            )
            await db.commit()
    finally:
        await db.close()

    # Init supervisor
    supervisor = SwarmSupervisor(db_path=db_path)
    await supervisor.initialize()

    # Dispatch tasks. The invalid one should be marked INVALIDATED and not dispatched.
    # The valid one should be dispatched.
    # We call dispatch_optimal_hypotheses directly.
    # We first need to patch the topology index for the test
    class DummyTopo:
        def __init__(self, db):
            self.db = db
            self.tasks = [
                {"id": "hyp-slop", "payload": json.dumps({"content": "This is a hallucinated LLM plan without latent basis"})},
                {"id": "hyp-valid", "payload": json.dumps(valid_hypothesis)}
            ]
        async def sync(self):
            pass
        def get_next_optimal_task(self, in_flight):
            for t in self.tasks:
                if t["id"] not in in_flight:
                    return t
            return None
            
    supervisor._topo = DummyTopo(supervisor._db)
    
    class DummyQueue:
        def full(self):
            return False

    # We need a dummy worker pool so it doesn't actually process it
    class DummyWorkerPool:
        def __init__(self):
            self._queue = DummyQueue()
        def dispatch_nowait(self, task_id):
            pass
        async def stop(self):
            pass
    supervisor.worker_pool = DummyWorkerPool()

    try:
        # Execute
        dispatched = await supervisor.dispatch_optimal_hypotheses(count=2)
        
        # It should only dispatch 1 valid task
        assert dispatched == 1
        
        # Check DB status
        db2 = await connect_async(db_path)
        try:
            async with db2.execute("SELECT status FROM system_hypotheses WHERE id = 'hyp-slop'") as cur:
                status_slop = (await cur.fetchone())[0]
                assert status_slop == "INVALIDATED"
                
            async with db2.execute("SELECT status FROM system_hypotheses WHERE id = 'hyp-valid'") as cur:
                status_valid = (await cur.fetchone())[0]
                assert status_valid == "IN_FLIGHT"
        finally:
            await db2.close()
    finally:
        await supervisor.shutdown()
