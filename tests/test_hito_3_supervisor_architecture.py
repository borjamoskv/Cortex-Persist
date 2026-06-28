import asyncio
import json
import logging
import os
import uuid
import pytest
import aiosqlite
from datetime import datetime, timezone

from cortex.swarm.supervisor import SwarmSupervisor
from cortex.swarm.legion import SwarmAgent, SwarmSignal
from cortex.swarm.state_store import CausalStateStore
from cortex.database.schema import CREATE_FACTS


# Mock Agent for testing
class TestAgent(SwarmAgent):
    async def execute(self, target: str) -> SwarmSignal:
        await asyncio.sleep(0.01)  # Small processing time
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status="SUCCESS",
            payload={
                "test_data": "ok",
                "exergy_seal": "C5_REAL_SOVEREIGN_ISOMORPHISM_PROVENANCE_LEVIATHAN_2026_XYZ_98765",
            },
            metrics={"exergy": 1.0},
        )


# Mock CausalClosureGuard to prevent actual Ledger calls in tests
@pytest.fixture(autouse=True)
def mock_causal_guard(monkeypatch):
    class MockGuard:
        def verify_closure(self, proposal):
            pass

    import cortex.swarm.state_store

    monkeypatch.setattr(cortex.swarm.state_store, "CausalClosureGuard", MockGuard)


async def setup_db(path: str):
    db = await aiosqlite.connect(path, isolation_level=None)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA busy_timeout=5000;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute(CREATE_FACTS)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS system_hypotheses (
            id UUID PRIMARY KEY,
            fact_id INTEGER,
            statement TEXT NOT NULL,
            probability FLOAT NOT NULL DEFAULT 0.5,
            svi FLOAT NOT NULL DEFAULT 1.0,
            evi FLOAT NOT NULL DEFAULT 0.0,
            cost FLOAT NOT NULL DEFAULT 1.0,
            impact FLOAT NOT NULL DEFAULT 1.0,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            resolution_reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS hypothesis_edges (
            parent_id UUID NOT NULL,
            child_id UUID NOT NULL,
            edge_weight REAL NOT NULL DEFAULT 1.0,
            relation_type TEXT NOT NULL DEFAULT 'requires',
            confidence REAL NOT NULL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            PRIMARY KEY(parent_id, child_id)
        )
    """)
    await db.execute("CREATE TABLE IF NOT EXISTS cortex_meta (key TEXT PRIMARY KEY, value TEXT)")
    await db.execute(
        "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES ('hypothesis_graph_version', '1')"
    )
    return db


@pytest.mark.asyncio
async def test_supervisor_pipeline_end_to_end():
    db_path = f"/tmp/supervisor_test_{uuid.uuid4().hex}.db"
    db = await setup_db(db_path)

    # Insert 5 tasks
    valid_payload = json.dumps(
        {
            "latent_basis": {
                "inputs": [],
                "model": "rule_based",
                "posterior": 0.99,
                "inferred_state": {},
            },
            "proposed_intervention": {
                "action_name": "test",
                "parameters": {},
                "predicted_outcomes": {},
                "confidence": 0.9,
            },
        }
    )
    for i in range(5):
        await db.execute(
            "INSERT INTO system_hypotheses (id, statement, probability, svi, cost, impact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (f"hyp-{i}", valid_payload, 0.9, 1.0, 1.0, 1.0, "ACTIVE", "2024-01-01T00:00:00Z"),
        )
    await db.close()

    # Initialize Supervisor
    supervisor = SwarmSupervisor(
        db_path=db_path, agent_factory=TestAgent, concurrency=5, bus_maxsize=10
    )
    await supervisor.initialize()

    try:
        # Dispatch tasks
        dispatched = await supervisor.dispatch_optimal_hypotheses(count=5)
        assert dispatched == 5

        # Wait for processing
        await asyncio.sleep(0.5)

        # Verify State was mutated by StateStore
        verify_db = await aiosqlite.connect(db_path)
        async with verify_db.execute(
            "SELECT count(*) FROM system_hypotheses WHERE status = 'COMPLETED'"
        ) as cur:
            completed = (await cur.fetchone())[0]

        await verify_db.close()
        assert completed == 5, "All 5 tasks should be COMPLETED"
    finally:
        await supervisor.shutdown()
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_ghost_state_recovery():
    db_path = f"/tmp/ghost_recovery_{uuid.uuid4().hex}.db"
    db = await setup_db(db_path)

    now = datetime.now(timezone.utc).isoformat()
    tasks = [
        ("hyp-0", "Stmt", 1.0, 1.0, 1.0, 1.0, "IN_FLIGHT", now),
        ("hyp-1", "Stmt", 1.0, 1.0, 1.0, 1.0, "IN_FLIGHT", now),
        ("hyp-2", "Stmt", 1.0, 1.0, 1.0, 1.0, "ACTIVE", now),
    ]
    await db.executemany(
        "INSERT INTO system_hypotheses (id, statement, probability, evi, cost, impact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        tasks,
    )
    await db.close()

    # Initialize state store to test recovery directly
    store = CausalStateStore(db_path)
    recovered = await store.recover_in_flight_tasks()

    assert recovered == 2

    verify_db = await aiosqlite.connect(db_path)
    async with verify_db.execute(
        "SELECT count(*) FROM system_hypotheses WHERE status = 'ACTIVE'"
    ) as cur:
        active = (await cur.fetchone())[0]

    assert active == 3, "2 IN_FLIGHT + 1 originally ACTIVE = 3 ACTIVE"

    await verify_db.close()
    await store.close()
    if os.path.exists(db_path):
        os.remove(db_path)
