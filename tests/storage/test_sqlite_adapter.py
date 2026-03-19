"""
Tests for StorageAdapter protocol conformance and SQLiteAdapter behavior.

Legion-Omega hardened: OOM (large batches), Intruder (isinstance checks),
Entropy (health_check resilience), Chronos (empty params safety).
"""

from __future__ import annotations

import aiosqlite
import pytest
import pytest_asyncio

from cortex.storage.adapter import StorageAdapter
from cortex.storage.sqlite_adapter import SQLiteAdapter


@pytest_asyncio.fixture
async def sqlite_adapter(tmp_path):
    """In-memory SQLite connection wrapped in SQLiteAdapter."""
    db = tmp_path / "test.db"
    conn = await aiosqlite.connect(str(db))
    await conn.executescript("CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT);")
    await conn.commit()
    adapter = SQLiteAdapter(conn)
    yield adapter
    await conn.close()


# ─── Protocol Conformance ────────────────────────────────────────────


def test_sqlite_adapter_is_storage_adapter(tmp_path):
    """SQLiteAdapter must satisfy StorageAdapter at runtime (Intruder check)."""
    import asyncio

    import aiosqlite

    async def _check():
        conn = await aiosqlite.connect(":memory:")
        adapter = SQLiteAdapter(conn)
        assert isinstance(adapter, StorageAdapter), (
            "SQLiteAdapter must satisfy the StorageAdapter runtime protocol"
        )
        await conn.close()

    asyncio.run(_check())


# ─── execute ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_returns_cursor(sqlite_adapter):
    await sqlite_adapter.execute("INSERT INTO facts (content) VALUES (?)", ("hello",))
    await sqlite_adapter.commit()
    cursor = await sqlite_adapter.execute("SELECT * FROM facts")
    rows = await cursor.fetchall()
    assert len(rows) == 1
    # Cursor rows are tuples by default in aiosqlite if not using Row factory
    assert rows[0][1] == "hello"


@pytest.mark.asyncio
async def test_fetch_all_returns_dicts(sqlite_adapter):
    await sqlite_adapter.execute("INSERT INTO facts (content) VALUES (?)", ("hello",))
    await sqlite_adapter.commit()
    rows = await sqlite_adapter.fetch_all("SELECT * FROM facts")
    assert len(rows) == 1
    assert rows[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_fetch_all_returns_empty_for_no_match(sqlite_adapter):
    rows = await sqlite_adapter.fetch_all("SELECT * FROM facts WHERE content = ?", ("ghost",))
    assert rows == []


# ─── execute_insert ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_insert_returns_rowid(sqlite_adapter):
    row_id = await sqlite_adapter.execute_insert(
        "INSERT INTO facts (content) VALUES (?)", ("inserted",)
    )
    assert row_id == 1


@pytest.mark.asyncio
async def test_execute_insert_sequential_ids(sqlite_adapter):
    id1 = await sqlite_adapter.execute_insert("INSERT INTO facts (content) VALUES (?)", ("a",))
    id2 = await sqlite_adapter.execute_insert("INSERT INTO facts (content) VALUES (?)", ("b",))
    assert id2 > id1


# ─── executemany ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_executemany_empty_list_is_noop(sqlite_adapter):
    """Entropy check: empty params list must not raise."""
    await sqlite_adapter.executemany("INSERT INTO facts (content) VALUES (?)", [])
    rows = await sqlite_adapter.fetch_all("SELECT COUNT(*) AS n FROM facts")
    assert rows[0]["n"] == 0


@pytest.mark.asyncio
async def test_executemany_batch_insert(sqlite_adapter):
    """OOM check: 1000-item batch must complete without error."""
    params = [(f"fact_{i}",) for i in range(1000)]
    await sqlite_adapter.executemany("INSERT INTO facts (content) VALUES (?)", params)
    await sqlite_adapter.commit()
    rows = await sqlite_adapter.fetch_all("SELECT COUNT(*) AS n FROM facts")
    assert rows[0]["n"] == 1000


# ─── commit ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_commit_persists_data(sqlite_adapter, tmp_path):
    """Data written + committed must survive a new connection."""
    await sqlite_adapter.execute_insert("INSERT INTO facts (content) VALUES (?)", ("durable",))
    await sqlite_adapter.commit()
    # Re-open the same db
    db = tmp_path / "test.db"
    conn2 = await aiosqlite.connect(str(db))
    adapter2 = SQLiteAdapter(conn2)
    rows = await adapter2.fetch_all("SELECT content FROM facts")
    await conn2.close()
    assert any(r["content"] == "durable" for r in rows)


# ─── health_check ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_check_alive(sqlite_adapter):
    """Health check must return True on a live connection."""
    result = await sqlite_adapter.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_health_check_closed_conn_returns_false(tmp_path):
    """Entropy check: health_check must return False (not raise) on closed conn."""
    db = tmp_path / "dead.db"
    conn = await aiosqlite.connect(str(db))
    adapter = SQLiteAdapter(conn)
    await conn.close()
    result = await adapter.health_check()
    assert result is False


# ─── executescript ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_executescript_creates_table(sqlite_adapter):
    await sqlite_adapter.executescript(
        "CREATE TABLE IF NOT EXISTS test_script (id INTEGER PRIMARY KEY);"
    )
    rows = await sqlite_adapter.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='test_script'"
    )
    assert len(rows) == 1
