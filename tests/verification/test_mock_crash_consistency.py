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
async def engine(tmp_path: Path, monkeypatch):
    """Create a CortexEngine with a temp database, close after test."""
    from cortex.engine import CortexEngine

    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "1")
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


@pytest.mark.asyncio
async def test_crash_before_causal_write(engine):
    """
    Test scenario where the system crashes before causal write authorization.
    Expected: No DB mutation and no Ledger mutation.
    """
    with patch(
        "cortex.engine.core.store_mixin.causal_write",
        side_effect=InducedCrashError("Crash before causal_write"),
    ):
        try:
            await engine.store(project="TEST", content='{"key": "val"}', source="cli")
        except InducedCrashError:
            pass

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST'")
        fact_count = (await cursor.fetchone())[0]
        assert fact_count == 0, "Fact should not be written to DB"

        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, "Transaction should not be written to Ledger"


@pytest.mark.asyncio
async def test_crash_after_ledger_before_db_write(engine):
    """
    Test scenario where Ledger (transaction) is updated but crash occurs before DB fact write completes.
    Since they share the same SQLite connection (and transaction), the crash should rollback the Ledger write.
    """
    from cortex.engine.core import store_mixin

    async def crashing_insert_fact_record(*args, **kwargs):
        raise InducedCrashError("Crash inside db insert")

    with patch(
        "cortex.engine.core.store_mixin.insert_fact_record", new=crashing_insert_fact_record
    ):
        try:
            await engine.store(project="TEST", content='{"key": "val2"}', source="cli")
        except InducedCrashError:
            pass

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST'")
        fact_count = (await cursor.fetchone())[0]
        assert fact_count == 0, "Fact write should not exist"

        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, (
            "Ledger transaction should be rolled back due to uncommitted transaction"
        )


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
            await engine.store(project="TEST", content='{"key": "val3"}', source="cli")
        except InducedCrashError:
            pass

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST'")
        fact_count = (await cursor.fetchone())[0]
        assert fact_count == 0, "Fact write should be rolled back"

        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, "Transaction should be rolled back"
