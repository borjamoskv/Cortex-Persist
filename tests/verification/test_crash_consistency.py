import pytest
import sqlite3
import asyncio
from unittest.mock import patch, AsyncMock
import logging
import os
from pathlib import Path
from cortex.database.core import causal_write

logger = logging.getLogger(__name__)

class InducedCrashError(Exception):
    """Exception raised specifically for simulating a system crash."""
    pass

@pytest.fixture
async def engine(tmp_path: Path):
    """Create a CortexEngine with a temp database, close after test."""
    from cortex.engine import CortexEngine

    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
    db = str(tmp_path / "test_crash.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()

    # Ensure causal_edges exists
    from cortex.engine.flow.causality import AsyncCausalGraph

    async with e.session() as conn:
        cg = AsyncCausalGraph(conn)
        await cg.ensure_table()

    yield e
    await e.close()
    if "CORTEX_SKIP_EXERGY_VALIDATION" in os.environ:
        del os.environ["CORTEX_SKIP_EXERGY_VALIDATION"]
    if "CORTEX_NO_TAINT_ENFORCE" in os.environ:
        del os.environ["CORTEX_NO_TAINT_ENFORCE"]

@pytest.mark.asyncio
async def test_crash_before_causal_write(engine):
    """
    Test scenario where the system crashes before causal write authorization.
    Expected: No DB mutation and no Ledger mutation.
    """
    with patch("cortex.engine.core.store_mixin.causal_write", side_effect=InducedCrashError("Crash before causal_write")):
        try:
            await engine.store(
                project="TEST", 
                action="CRASH_TEST", 
                content={"key": "val"}
            )
        except InducedCrashError:
            pass

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST' AND action = 'CRASH_TEST'")
        fact_count = (await cursor.fetchone())[0]
        assert fact_count == 0, "Fact should not be written to DB"
        
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST' AND action = 'CRASH_TEST'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, "Transaction should not be written to Ledger"


@pytest.mark.asyncio
async def test_crash_after_db_write_before_ledger(engine):
    """
    Test scenario where DB is updated but crash occurs before ledger logic completes.
    Since they share the same SQLite connection (and transaction), the crash should rollback the DB write.
    """
    async def crashing_log_transaction(*args, **kwargs):
        raise InducedCrashError("Crash inside ledger logic")
    
    with patch.object(engine, "_log_transaction", new=crashing_log_transaction):
        try:
            await engine.store(
                project="TEST", 
                action="CRASH_TEST_2", 
                content={"key": "val2"}
            )
        except InducedCrashError:
            pass
            
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST' AND action = 'CRASH_TEST_2'")
        fact_count = (await cursor.fetchone())[0]
        # Because we are using an async transaction context, if an exception propagates, 
        # aiosqlite should issue a ROLLBACK automatically.
        assert fact_count == 0, "Fact write should be rolled back due to uncommitted transaction"
        
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST' AND action = 'CRASH_TEST_2'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, "Transaction should not exist"


@pytest.mark.asyncio
async def test_crash_during_commit(engine):
    """
    Test scenario where everything finishes, but commit fails.
    Expected: Rollback of both DB and Ledger writes.
    """
    async def crashing_commit(*args, **kwargs):
        raise InducedCrashError("Crash during commit")

    with patch("aiosqlite.Connection.commit", new=crashing_commit):
        try:
            await engine.store(
                project="TEST", 
                action="CRASH_TEST_3", 
                content={"key": "val3"}
            )
        except InducedCrashError:
            pass

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST' AND action = 'CRASH_TEST_3'")
        fact_count = (await cursor.fetchone())[0]
        assert fact_count == 0, "Fact write should be rolled back"
        
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST' AND action = 'CRASH_TEST_3'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, "Transaction should be rolled back"
