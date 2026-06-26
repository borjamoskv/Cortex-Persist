# [C5-REAL] Exergy-Maximized
import asyncio
import multiprocessing
import os
import signal
import sqlite3
import time
from pathlib import Path

os.environ["CORTEX_NO_EMBED"] = "1"

import pytest

from cortex.engine.core.cortex_engine import CortexEngine

def _writer_process_target(db_path: Path, sync_event: multiprocessing.Event, fault_point: str):
    """Worker process that triggers sync_event at precise execution points."""
    async def _run():
        try:
            engine = CortexEngine(db_path=str(db_path))
            engine._synthesize_skill("optimization")
            print("WORKER: Calling engine.start()")
            await engine.start()
            
            if fault_point == "before_sqlite":
                print("WORKER: Setting sync_event (before_sqlite)")
                sync_event.set()
                await asyncio.sleep(10)
                
            # Ensure ledger is initialized before monkeypatching
            await engine._get_or_create_ledger()
            original_checkpoint = engine._ledger.create_checkpoint_async
            
            async def _faulty_checkpoint(*args, **kwargs):
                print(f"WORKER: In _faulty_checkpoint, fault_point={fault_point}")
                if fault_point == "after_sqlite_before_ledger":
                    print("WORKER: Setting sync_event (after_sqlite_before_ledger)")
                    sync_event.set()
                    print("WORKER: Waiting for SIGKILL (after_sqlite_before_ledger)")
                    await asyncio.sleep(10) # Wait for SIGKILL
                return await original_checkpoint(*args, **kwargs)
                
            engine._ledger.create_checkpoint_async = _faulty_checkpoint
            
            print("WORKER: Calling engine.facts.store()")
            await engine.facts.store(project="test", content="crash_test_payload", tenant_id="test_tenant", source="test")
            if fault_point == "after_commit":
                print("WORKER: Setting sync_event (after_commit)")
                sync_event.set()
                print("WORKER: Waiting for SIGKILL (after_commit)")
                await asyncio.sleep(10)
            
            print("WORKER: Closing engine")
            await engine.close()
        except Exception as e:
            print(f"WORKER ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(_run())


@pytest.mark.asyncio
@pytest.mark.parametrize("fault_point", [
    "before_sqlite",
    "after_sqlite_before_ledger",
    "after_commit"
])
async def test_sigkill_crash_consistency(tmp_path: Path, fault_point: str):
    """
    Verifies that the database and ledger remain consistent under hard SIGKILL termination.
    SQLite WAL recovery should cleanly discard uncommitted transactions.
    """
    db_path = tmp_path / "cortex_assurance.db"
    
    # 1. Initialize schema
    engine = CortexEngine(db_path=str(db_path))
    engine._synthesize_skill("optimization")
    await engine.start()
    await engine.close()
    
    # 2. Spawn worker
    sync_event = multiprocessing.Event()
    p = multiprocessing.Process(target=_writer_process_target, args=(db_path, sync_event, fault_point))
    p.start()
    
    # 3. Wait for worker to reach the vulnerability window
    reached = sync_event.wait(timeout=30.0)
    assert reached, f"Worker did not reach {fault_point}"
    
    # 4. Annihilate worker abruptly (SIGKILL cannot be caught by try/finally or signal handlers)
    os.kill(p.pid, signal.SIGKILL)
    p.join()
    
    # 5. Verify integrity (Recovery)
    engine_verify = CortexEngine(db_path=str(db_path))
    engine_verify._synthesize_skill("optimization")
    await engine_verify.start()
    
    # Execute raw query to bypass cache
    async with engine_verify.session() as conn:
        cursor = await conn.execute("SELECT content FROM facts WHERE tenant_id='test_tenant'")
        rows = await cursor.fetchall()
        
    # Consistency Assertions
    if fault_point in ("before_sqlite", "after_sqlite_before_ledger"):
        # The transaction was never fully committed, WAL should discard it
        assert len(rows) == 0, f"Integrity Breach: Fact leaked into DB despite SIGKILL at {fault_point}"
    elif fault_point == "after_commit":
        # The transaction committed completely
        assert len(rows) == 1, "Integrity Breach: Fact lost despite completing commit"
        
        # Verify via engine to test decryption
        facts = await engine_verify.facts.search(query="crash_test_payload", tenant_id="test_tenant")
        assert len(facts) > 0, "Failed to decrypt/retrieve fact from engine"
        assert facts[0].content == "crash_test_payload"

    # 6. Verify SQLite integrity PRAGMA
    async with engine_verify.session() as conn:
        cursor = await conn.execute("PRAGMA integrity_check;")
        integrity = await cursor.fetchone()
        assert integrity[0] == "ok", "Database corruption detected after SIGKILL"

    await engine_verify.close()
