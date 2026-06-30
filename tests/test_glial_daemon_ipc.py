# [C5-REAL] Exergy-Maximized
import asyncio
import os
import pytest
from pathlib import Path

from cortex.engine import CortexEngine
from cortex.events.loop import start_glial_daemon, stop_glial_daemon
from cortex.ipc.client import dispatch_store_batch
from cortex_extensions.policy.memory_os import MemoryOS, MemoryTier

@pytest.fixture
async def engine(tmp_path: Path):
    # Unblock tests from thermodynamic enforcement
    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    
    db = str(tmp_path / "test_glial_ipc.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()
    
    yield e
    await e.close()
    
    if "CORTEX_SKIP_EXERGY_VALIDATION" in os.environ:
        del os.environ["CORTEX_SKIP_EXERGY_VALIDATION"]

@pytest.mark.asyncio
async def test_glial_daemon_ipc_flow(engine):
    # 1. Start Glial Daemon IPC server with our test engine
    await start_glial_daemon(engine)
    
    try:
        # 2. Prepare a fact to dispatch via IPC
        fact = {
            "project": "ipc_test",
            "content": "Glial Daemon IPC writes immutably.",
            "fact_type": "knowledge",
            "meta": {},
            "tags": ["ipc", "test"]
        }
        
        # 3. Call dispatch_store_batch
        response = await dispatch_store_batch([fact])
        assert response.get("status") == "ok"
        assert response.get("stored") == 1
        
        # 4. Verify that the fact was indeed stored in the engine's database
        facts = await engine.facts.recall(project="ipc_test")
        assert len(facts) == 1
        assert facts[0].content == "Glial Daemon IPC writes immutably."
        
    finally:
        # 5. Clean up/stop daemon
        await stop_glial_daemon()

@pytest.mark.asyncio
async def test_memory_os_semantic_write_via_ipc(engine):
    # 1. Start Glial Daemon IPC server
    await start_glial_daemon(engine)
    
    try:
        # 2. Initialize MemoryOS with this engine
        mem_os = MemoryOS(engine=engine)
        
        # 3. Write semantic memory, which should route through IPC
        result = await mem_os.write(MemoryTier.SEMANTIC, "mem_os_ipc", "MemoryOS routes semantic writes via IPC.", 1.0)
        assert result is True
        
        # 4. Verify that the fact was written to the engine
        facts = await engine.facts.recall(project="mem_os_ipc")
        assert len(facts) == 1
        assert facts[0].content == "MemoryOS routes semantic writes via IPC."
        
    finally:
        await stop_glial_daemon()
