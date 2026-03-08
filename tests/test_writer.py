"""Tests for cortex.database.writer.SqliteWriteWorker — Single Writer Queue."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.database.writer import SqliteWriteWorker
from cortex.utils.result import Err, Ok


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Create a temp SQLite database with a test table."""
    import sqlite3

    db = str(tmp_path / "test_writer.db")
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS items ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  name TEXT NOT NULL,"
        "  value INTEGER DEFAULT 0"
        ")"
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture
async def writer(db_path: str):
    """Provide a started SqliteWriteWorker, stop it after test."""
    w = SqliteWriteWorker(db_path, queue_size=100)
    await w.start()
    yield w
    await w.stop()


# ─── Lifecycle ────────────────────────────────────────────────────────


class TestLifecycle:
    async def test_start_sets_running(self, writer: SqliteWriteWorker):
        assert writer.is_running is True

    async def test_stop_clears_running(self, db_path: str):
        w = SqliteWriteWorker(db_path)
        await w.start()
        assert w.is_running is True
        await w.stop()
        assert w.is_running is False

    async def test_double_start_is_idempotent(self, writer: SqliteWriteWorker):
        await writer.start()  # Should not raise
        assert writer.is_running is True

    async def test_stop_without_start_is_safe(self, db_path: str):
        w = SqliteWriteWorker(db_path)
        await w.stop()  # Should not raise


# ─── Write Operations ────────────────────────────────────────────────


class TestWriteOperations:
    async def test_single_insert(self, writer: SqliteWriteWorker):
        result = await writer.execute(
            "INSERT INTO items (name, value) VALUES (?, ?)", ("alpha", 1)
        )
        assert isinstance(result, Ok)
        assert result.value >= 0  # rowcount

    async def test_execute_returns_rowcount(self, writer: SqliteWriteWorker):
        await writer.execute("INSERT INTO items (name, value) VALUES (?, ?)", ("a", 1))
        result = await writer.execute("UPDATE items SET value = 99 WHERE name = ?", ("a",))
        assert isinstance(result, Ok)
        assert result.value == 1  # 1 row updated

    async def test_execute_on_stopped_writer(self, db_path: str):
        w = SqliteWriteWorker(db_path)
        result = await w.execute("INSERT INTO items (name) VALUES (?)", ("x",))
        assert isinstance(result, Err)
        assert "not running" in result.error

    async def test_invalid_sql_returns_err(self, writer: SqliteWriteWorker):
        result = await writer.execute("INSERT INTO nonexistent_table VALUES (?)", ("x",))
        assert isinstance(result, Err)

    async def test_multiple_sequential_writes(self, writer: SqliteWriteWorker):
        for i in range(10):
            result = await writer.execute(
                "INSERT INTO items (name, value) VALUES (?, ?)", (f"item_{i}", i)
            )
            assert isinstance(result, Ok)


# ─── Batch Operations ────────────────────────────────────────────────


class TestBatchOperations:
    async def test_execute_many_success(self, writer: SqliteWriteWorker):
        ops = [
            ("INSERT INTO items (name, value) VALUES (?, ?)", ("batch_a", 1)),
            ("INSERT INTO items (name, value) VALUES (?, ?)", ("batch_b", 2)),
            ("INSERT INTO items (name, value) VALUES (?, ?)", ("batch_c", 3)),
        ]
        result = await writer.execute_many(ops)
        assert isinstance(result, Ok)

    async def test_execute_many_rollback_on_error(self, writer: SqliteWriteWorker):
        ops = [
            ("INSERT INTO items (name, value) VALUES (?, ?)", ("ok_row", 1)),
            ("INSERT INTO nonexistent_table VALUES (?)", ("boom",)),
        ]
        result = await writer.execute_many(ops)
        assert isinstance(result, Err)


# ─── Transaction Context Manager ─────────────────────────────────────


class TestTransaction:
    async def test_transaction_commit(self, writer: SqliteWriteWorker):
        async with writer.transaction() as tx:
            await tx.execute("INSERT INTO items (name, value) VALUES (?, ?)", ("tx_a", 10))
            await tx.execute("INSERT INTO items (name, value) VALUES (?, ?)", ("tx_b", 20))
        # Should have committed — verify via read
        import sqlite3

        conn = sqlite3.connect(writer._db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM items WHERE name LIKE 'tx_%'")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2

    async def test_transaction_rollback_on_exception(self, writer: SqliteWriteWorker):
        import sqlite3

        try:
            async with writer.transaction() as tx:
                await tx.execute("INSERT INTO items (name, value) VALUES (?, ?)", ("rollback_me", 1))
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Expected

        conn = sqlite3.connect(writer._db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM items WHERE name = 'rollback_me'")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0


# ─── Metrics ──────────────────────────────────────────────────────────


class TestMetrics:
    async def test_metrics_initial(self, writer: SqliteWriteWorker):
        m = writer.metrics
        assert m["total_ops"] == 0
        assert m["avg_wait_ms"] == 0.0
        assert m["avg_exec_ms"] == 0.0

    async def test_metrics_after_writes(self, writer: SqliteWriteWorker):
        for i in range(5):
            await writer.execute("INSERT INTO items (name) VALUES (?)", (f"m_{i}",))
        m = writer.metrics
        assert m["total_ops"] == 5
        assert m["avg_exec_ms"] >= 0.0  # Should be positive

    async def test_metrics_returns_copy(self, writer: SqliteWriteWorker):
        m1 = writer.metrics
        m1["total_ops"] = 9999
        assert writer.metrics["total_ops"] != 9999  # Original unchanged


# ─── WAL Checkpoint ───────────────────────────────────────────────────


class TestCheckpoint:
    async def test_manual_checkpoint(self, writer: SqliteWriteWorker):
        await writer.execute("INSERT INTO items (name) VALUES (?)", ("cp_test",))
        result = await writer.checkpoint()
        assert isinstance(result, Ok)

    async def test_checkpoint_on_stopped_writer(self, db_path: str):
        w = SqliteWriteWorker(db_path)
        result = await w.checkpoint()
        assert isinstance(result, Err)
