"""Tests for Dimension 1: SQLite Extreme Topology."""

import sqlite3
import tempfile
from pathlib import Path

import aiosqlite
import pytest

from cortex.database.core import (
    connect,
    connect_writer,
)
from cortex.database.pool import CortexConnectionPool
from cortex.database.writer import SqliteWriteWorker


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        yield f.name


def get_pragma(conn, pragma_name):
    # Depending on async/sync and dictionary vs tuple row
    return conn.execute(f"PRAGMA {pragma_name}").fetchone()[0]


async def get_pragma_async(conn, pragma_name):
    async with conn.execute(f"PRAGMA {pragma_name}") as cursor:
        row = await cursor.fetchone()
        return row[0] if row else None


def test_mmap_pragma_set(temp_db):
    """Verify PRAGMA mmap_size returns configured value after connect()."""
    conn = connect(temp_db)
    mmap_size = get_pragma(conn, "mmap_size")
    # Should be 20GB or max supported by OS
    assert mmap_size > 0
    conn.close()


def test_wal_autocheckpoint_disabled_on_writer(temp_db):
    """Verify PRAGMA wal_autocheckpoint = 0 on writer connection."""
    conn = connect_writer(temp_db)
    wal_ac = get_pragma(conn, "wal_autocheckpoint")
    assert wal_ac == 0
    conn.close()


def test_read_only_sync(temp_db):
    """Verify read_only sync connection rejects writes."""
    # Setup table using normal connection
    conn_setup = connect(temp_db)
    conn_setup.execute("CREATE TABLE foo (id INTEGER)")
    conn_setup.close()

    conn_ro = connect(temp_db, read_only=True)
    with pytest.raises(sqlite3.OperationalError, match="attempt to write a readonly database"):
        conn_ro.execute("INSERT INTO foo VALUES (1)")
    conn_ro.close()


@pytest.mark.asyncio
async def test_read_only_pool_rejects_writes(temp_db):
    """Acquire pool conn, attempt INSERT, expect OperationalError."""
    # Setup table using normal async connection
    async with aiosqlite.connect(temp_db) as conn_setup:
        await conn_setup.execute("CREATE TABLE foo (id INTEGER)")
        await conn_setup.commit()

    # The pool defaults to read_only=True
    pool = CortexConnectionPool(temp_db, min_connections=1, max_connections=2)
    await pool.initialize()

    async with pool.acquire() as conn:
        with pytest.raises(sqlite3.OperationalError, match="attempt to write a readonly database"):
            await conn.execute("INSERT INTO foo VALUES (1)")
            await conn.commit()

    await pool.close()


@pytest.mark.asyncio
async def test_writer_checkpoints_on_stop(temp_db):
    """Verify SqliteWriteWorker runs checkpoint before closing."""
    # Setup table
    async with aiosqlite.connect(temp_db) as conn_setup:
        await conn_setup.execute("CREATE TABLE foo (id INTEGER)")
        await conn_setup.execute("PRAGMA journal_mode=WAL")
        await conn_setup.commit()

    writer = SqliteWriteWorker(temp_db)
    await writer.start()

    # Write some data
    await writer.execute("INSERT INTO foo VALUES (1)")
    await writer.execute("INSERT INTO foo VALUES (2)")

    # The WAL file should exist and have data
    wal_path = Path(temp_db + "-wal")
    assert wal_path.exists()
    size_before = wal_path.stat().st_size

    await writer.stop()

    # TRUNCATE checkpoint zero-fills or truncates the WAL
    # If it's the last connection closing, the WAL file gets deleted cleanly
    if wal_path.exists():
        size_after = wal_path.stat().st_size
        assert size_after < size_before or size_after == 0


@pytest.mark.asyncio
async def test_manual_checkpoint(temp_db):
    """Verify manual checkpoint method on SqliteWriteWorker."""
    # Setup table
    async with aiosqlite.connect(temp_db) as conn_setup:
        await conn_setup.execute("CREATE TABLE foo (id INTEGER)")
        await conn_setup.execute("PRAGMA journal_mode=WAL")
        await conn_setup.commit()

    writer = SqliteWriteWorker(temp_db)
    await writer.start()

    await writer.execute("INSERT INTO foo VALUES (1)")
    await writer.execute("INSERT INTO foo VALUES (2)")

    res = await writer.checkpoint()
    assert res.is_ok()
    # Number of pages checkpointed
    assert res.unwrap() >= 0

    await writer.stop()
