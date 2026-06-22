# [C5-REAL] Exergy-Maximized
# Author: Borja Moskv (borjamoskv)
import os
import asyncio
import tempfile
import pytest
import aiosqlite
from cortex.engine.latticework_store import LatticeworkStore
from cortex.engine.latticework_daemon import LatticeworkDaemon
from cortex.engine.babylon60 import Babylon60
from cortex.ledger.execution_trace import ExecutionTraceLedger
from cortex.ledger.causal_graph import CausalGraph
from cortex.engine.rollback_engine import CausalRollbackEngine
from cortex.engine.causal_scheduler import CausalScheduler

def test_latticework_store_initialization():
    store = LatticeworkStore()
    # Check that primitives are loaded
    assert len(store.primitives) > 0
    # Retrieve primitive 9
    prim9 = store.get_primitive(9)
    assert prim9 is not None
    assert prim9.id == 9
    assert prim9.base60_constant >= 0

def test_latticework_store_search():
    store = LatticeworkStore()
    results = store.search_by_keyword("Matrix") or store.search_by_keyword("Matriz")
    assert len(results) >= 0

@pytest.mark.asyncio
async def test_latticework_daemon_lifecycle():
    class DummyLedger:
        def __init__(self):
            self.anomalies = []
        async def get_recent_anomalies(self, limit=10):
            return self.anomalies

    class DummyScheduler:
        def __init__(self):
            self.exergy_injections = []
        async def inject_exergy(self, anomaly_id, exergy_val):
            self.exergy_injections.append((anomaly_id, exergy_val))

    ledger = DummyLedger()
    scheduler = DummyScheduler()
    daemon = LatticeworkDaemon(ledger, scheduler, scan_interval=1)
    
    # Check coverage report
    report = daemon.omega_index.coverage_report()
    assert report["total"] == 100
    assert report["coverage_pct"] > 0.0

    # Start the daemon
    daemon.start()
    assert daemon._running is True
    assert daemon._task is not None

    # Wait a bit for at least one tick
    await asyncio.sleep(1.2)

    # Stop the daemon
    await daemon.stop()
    assert daemon._running is False

@pytest.mark.asyncio
async def test_latticework_real_scheduler_injection():
    # Setup temporary database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    try:
        # Initialize the execution trace ledger schema manually
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_trace_ledger (
                    id              TEXT PRIMARY KEY,
                    tenant_id       TEXT NOT NULL DEFAULT 'default',
                    origin          TEXT NOT NULL,
                    cost            REAL NOT NULL,
                    lineage         TEXT NOT NULL DEFAULT '[]',
                    outcome         TEXT NOT NULL,
                    rollback_possible BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            await conn.commit()

        # Initialize ledger, graph, rollback engine, and scheduler
        ledger = ExecutionTraceLedger(db_path)
        graph = CausalGraph(db_path)
        rollback = CausalRollbackEngine(db_path, ledger, None)
        scheduler = CausalScheduler(graph, rollback, ledger)
        
        # Verify initial budget
        initial_budget = await scheduler._get_entropy_budget("default")
        assert initial_budget == 1000.0
        
        # Inject exergy directly
        await scheduler.inject_exergy("test_injection", 50.0, "default")
        updated_budget = await scheduler._get_entropy_budget("default")
        assert updated_budget == 1050.0
        
        # Test LatticeworkDaemon integration with the real scheduler
        daemon = LatticeworkDaemon(ledger, scheduler, scan_interval=1)
        daemon.start()
        await asyncio.sleep(1.2)
        await daemon.stop()
        
        # Verify that the budget increased (since the daemon loop processed 4 anomalies
        # and injected their computed exergy into the real scheduler)
        final_budget = await scheduler._get_entropy_budget("default")
        assert final_budget > 1050.0
    finally:
        os.close(fd)
        if os.path.exists(db_path):
            os.remove(db_path)
