"""Tests for cortex.db_writer — SqliteWriteWorker (Single Writer Queue)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from cortex.db_writer import SqliteWriteWorker
from cortex.result import Err, Ok


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Provide a temporary SQLite database path."""
    return str(tmp_path / "test_writer.db")


@pytest.fixture
async def writer(db_path: str):
    """Create, start, and yield a SqliteWriteWorker; stop on exit."""
    w = SqliteWriteWorker(db_path)
    await w.start()
    # Create test table
    result = await w.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, val TEXT)")
    assert isinstance(result, Ok)
    yield w
    await w.stop()


# ─── Lifecycle Tests ──────────────────────────────────────────────────


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self, db_path: str):
        w = SqliteWriteWorker(db_path)
        assert not w.is_running
        await w.start()
        assert w.is_running
        await w.stop()
        assert not w.is_running

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self, db_path: str):
        w = SqliteWriteWorker(db_path)
        await w.start()
        await w.start()  # Should not raise
        assert w.is_running
        await w.stop()

    @pytest.mark.asyncio
    async def test_execute_before_start(self, db_path: str):
        w = SqliteWriteWorker(db_path)
        result = await w.execute("SELECT 1")
        assert isinstance(result, Err)
        assert "not running" in result.error


# ─── Write Tests ──────────────────────────────────────────────────────


class TestWrites:
    @pytest.mark.asyncio
    async def test_single_insert(self, writer: SqliteWriteWorker):
        result = await writer.execute("INSERT INTO test (val) VALUES (?)", ("hello",))
        assert isinstance(result, Ok)
        assert result.value >= 0  # rowcount

    @pytest.mark.asyncio
    async def test_multiple_inserts(self, writer: SqliteWriteWorker):
        for i in range(50):
            result = await writer.execute("INSERT INTO test (val) VALUES (?)", (f"item-{i}",))
            assert isinstance(result, Ok)

    @pytest.mark.asyncio
    async def test_invalid_sql_returns_err(self, writer: SqliteWriteWorker):
        result = await writer.execute("INSERT INTO nonexistent (x) VALUES (?)", (1,))
        assert isinstance(result, Err)
        assert "SQLite write error" in result.error


# ─── Transaction Tests ────────────────────────────────────────────────


class TestTransactions:
    @pytest.mark.asyncio
    async def test_transaction_commit(self, writer: SqliteWriteWorker):
        async with writer.transaction() as tx:
            r1 = await tx.execute("INSERT INTO test (val) VALUES (?)", ("tx1",))
            r2 = await tx.execute("INSERT INTO test (val) VALUES (?)", ("tx2",))
            assert isinstance(r1, Ok)
            assert isinstance(r2, Ok)

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_exception(self, writer: SqliteWriteWorker):
        with pytest.raises(ValueError):
            async with writer.transaction() as tx:
                await tx.execute("INSERT INTO test (val) VALUES (?)", ("will_rollback",))
                raise ValueError("forced error")

    @pytest.mark.asyncio
    async def test_execute_many(self, writer: SqliteWriteWorker):
        ops = [("INSERT INTO test (val) VALUES (?)", (f"batch-{i}",)) for i in range(10)]
        result = await writer.execute_many(ops)
        assert isinstance(result, Ok)
        assert result.value == 10


# ─── Concurrency Tests ───────────────────────────────────────────────


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_writes_serialized(self, writer: SqliteWriteWorker):
        """100 concurrent writes should all succeed without BUSY errors."""
        tasks = [
            writer.execute("INSERT INTO test (val) VALUES (?)", (f"conc-{i}",)) for i in range(100)
        ]
        results = await asyncio.gather(*tasks)
        ok_count = sum(1 for r in results if isinstance(r, Ok))
        assert ok_count == 100, f"Expected 100 Ok results, got {ok_count}"
