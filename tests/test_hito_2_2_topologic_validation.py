import asyncio
import os
import time
import uuid
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
import aiosqlite

from cortex.config import DB_PATH
from cortex.engine.causal.topological_arbitrage import TopologyIndex
from cortex.swarm.swarm_10k import SwarmCommander
from cortex.swarm.legion import SwarmSignal, AsyncSignalBus

# Helper function to set up in-memory DB for tests
async def setup_test_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(":memory:")
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
    await db.execute("INSERT OR IGNORE INTO cortex_meta (key, value) VALUES ('hypothesis_graph_version', '1')")
    await db.commit()
    return db

@pytest.mark.asyncio
async def test_cbr_ordering_strict():
    """Test that hypotheses are ordered correctly by CBR (highest first) and deterministic tie breaking."""
    db = await setup_test_db()
    
    # Insert 3 hypotheses. A has highest CBR. B and C have same CBR, tie broken by UUID
    now = datetime.now(timezone.utc).isoformat()
    
    # A: impact=10, prob=1.0, cost=1.0, svi=1.0 -> CBR=10.0
    id_a = str(uuid.uuid4())
    # B: impact=5, prob=1.0, cost=1.0, svi=1.0 -> CBR=5.0. 
    id_b = "11111111-1111-1111-1111-111111111111" # Lowest UUID for tie
    # C: same as B
    id_c = "99999999-9999-9999-9999-999999999999" # Highest UUID for tie
    
    await db.executemany(
        "INSERT INTO system_hypotheses (id, statement, probability, svi, cost, impact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (id_a, "Stmt A", 1.0, 1.0, 1.0, 10.0, 'ACTIVE', now),
            (id_b, "Stmt B", 1.0, 1.0, 1.0, 5.0, 'ACTIVE', now),
            (id_c, "Stmt C", 1.0, 1.0, 1.0, 5.0, 'ACTIVE', now)
        ]
    )
    await db.commit()
    
    topo = TopologyIndex(db)
    await topo.sync()
    
    # Get optimal task
    in_flight = set()
    t1 = topo.get_next_optimal_task(in_flight)
    assert t1["id"] == id_a, "Highest CBR must be selected first"
    in_flight.add(t1["id"])
    
    t2 = topo.get_next_optimal_task(in_flight)
    in_flight.add(t2["id"])
    t3 = topo.get_next_optimal_task(in_flight)
    
    # Tie breaking: descending sort by UUID because reverse=True applies to the tuple (CBR, ID)
    assert t2["id"] == id_c, "Tie break must select higher UUID when sorting DESC"
    assert t3["id"] == id_b, "Tie break must select lower UUID last"
    
    await db.close()

@pytest.mark.asyncio
async def test_starvation_decay_bounds():
    """Test that an old task with lower CBR overtakes a new task with higher CBR over time."""
    db = await setup_test_db()
    
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    new_time = datetime.now(timezone.utc).isoformat()
    
    id_old = str(uuid.uuid4())
    id_new = str(uuid.uuid4())
    
    # Old task: CBR = 1.0, Age = 2 hours. Boost = 1.0 * (1 + ln(2*3600/3600)) = 1 + ln(2) ~= 1.693
    # New task: CBR = 1.6, Age = 0 hours. Boost = 1.6 * (1 + ln(0/3600)) = 1.6
    await db.executemany(
        "INSERT INTO system_hypotheses (id, statement, probability, svi, cost, impact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (id_old, "Old Task", 1.0, 1.0, 1.0, 1.0, 'ACTIVE', old_time),
            (id_new, "New Task", 1.0, 1.0, 1.0, 1.6, 'ACTIVE', new_time),
        ]
    )
    await db.commit()
    
    topo = TopologyIndex(db)
    await topo.sync()
    t1 = topo.get_next_optimal_task(set())
    
    assert t1["id"] == id_old, "Old task with boosted CBR should overtake new task"
    
    await db.close()

@pytest.mark.asyncio
async def test_topology_extraction_scaling():
    """Test O(1) properties for 1000 hypotheses."""
    db = await setup_test_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Generate 1000 nodes
    tasks = []
    for i in range(1000):
        tasks.append((str(uuid.uuid4()), f"Stmt {i}", 1.0, 1.0, 1.0, float(i), 'ACTIVE', now))
        
    await db.executemany(
        "INSERT INTO system_hypotheses (id, statement, probability, svi, cost, impact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        tasks
    )
    await db.commit()
    
    start_build = time.perf_counter()
    topo = TopologyIndex(db)
    await topo.sync()
    end_build = time.perf_counter()
    
    start_extract = time.perf_counter()
    for _ in range(100):
        topo.get_next_optimal_task(set())
    end_extract = time.perf_counter()
    
    assert end_extract - start_extract < 1.0, "Extraction of 100 tasks must be under 1s"
    
    await db.close()

@pytest.mark.asyncio
async def test_scheduler_determinism():
    """Test that multiple runs on the exact same data yield the exact same trace."""
    db = await setup_test_db()
    now = "2026-06-26T10:00:00+00:00"
    
    tasks = []
    for i in range(100):
        tasks.append((f"id-{i}", f"Stmt {i}", 1.0, 1.0, 1.0, float(i%10), 'ACTIVE', now))
    
    await db.executemany(
        "INSERT INTO system_hypotheses (id, statement, probability, svi, cost, impact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        tasks
    )
    await db.commit()
    
    topo = TopologyIndex(db)
    await topo.sync()
    
    def extract_all():
        in_flight = set()
        trace = []
        for _ in range(100):
            t = topo.get_next_optimal_task(in_flight)
            if t:
                in_flight.add(t["id"])
                trace.append(t["id"])
        return trace
        
    trace_1 = extract_all()
    trace_2 = extract_all()
    
    assert trace_1 == trace_2, "Multiple runs must yield deterministic extraction order"
    assert len(trace_1) == 100, "Should extract all 100 tasks"
    
    await db.close()

@pytest.mark.asyncio
async def test_cascade_death_concurrent_drops(caplog):
    """Test that SwarmSignal for an INVALIDATED hypothesis is dropped by SwarmStateStore."""
    from cortex.swarm.state_store import CausalStateStore
    import tempfile
    import logging
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = os.path.join(tmpdir, "test_cascade.db")
        
        # Setup DB and insert INVALIDATED hypothesis
        async with aiosqlite.connect(test_db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_hypotheses (
                    id TEXT PRIMARY KEY,
                    statement TEXT,
                    probability REAL,
                    svi REAL,
                    cost REAL,
                    impact REAL,
                    status TEXT,
                    created_at TEXT
                )
            """)
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT INTO system_hypotheses (id, statement, probability, svi, cost, impact, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("hyp-1234", "Stmt", 1.0, 1.0, 1.0, 1.0, 'INVALIDATED', now)
            )
            await db.commit()
            
        store = CausalStateStore(test_db_path)
        await store.connect()
        
        signal = SwarmSignal(
            agent_id="ag-1",
            target="hyp-1234",
            status="SUCCESS",
            payload={"result": "data"},
            metrics={}
        )
        
        with caplog.at_level(logging.WARNING):
            await store.process_signal(signal)
            
        assert any("Dropping signal for hyp-1234: Hypothesis is INVALIDATED" in record.message for record in caplog.records)
        await store.close()
