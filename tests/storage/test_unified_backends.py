# [C5-REAL] Exergy-Maximized
"""
Tests for unified storage backend abstractions.
Verifies that all storage backends (SQLitePoolAdapter, PostgresBackend, TursoBackend)
strictly implement and satisfy the StorageAdapter runtime protocol.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from babylon60.storage.adapter import StorageAdapter
from babylon60.storage.postgres import PostgresBackend
from babylon60.storage.router import get_router
from babylon60.storage.sqlite_adapter import SQLitePoolAdapter
from babylon60.storage.turso import TursoBackend


def test_backends_conformance():
    """Verify all backend adapter classes strictly implement the StorageAdapter Protocol."""
    # Class-level check via issubclass
    assert issubclass(SQLitePoolAdapter, StorageAdapter), (
        "SQLitePoolAdapter must satisfy StorageAdapter"
    )
    assert issubclass(PostgresBackend, StorageAdapter), (
        "PostgresBackend must satisfy StorageAdapter"
    )
    assert issubclass(TursoBackend, StorageAdapter), "TursoBackend must satisfy StorageAdapter"


@pytest.mark.asyncio
async def test_sqlite_pool_adapter_operations(tmp_path):
    """Test SQLitePoolAdapter basic CRUD operations conforming to StorageAdapter."""
    from babylon60.database.pool import CortexConnectionPool

    db = tmp_path / "test_pool.db"
    pool = CortexConnectionPool(str(db), read_only=False)
    await pool.initialize()

    adapter = SQLitePoolAdapter(pool)

    # executescript
    await adapter.executescript("CREATE TABLE test_facts (id INTEGER PRIMARY KEY, content TEXT);")

    # execute_insert
    row_id = await adapter.execute_insert("INSERT INTO test_facts (content) VALUES (?)", ("hello",))
    assert row_id == 1

    # fetch_all
    rows = await adapter.fetch_all("SELECT * FROM test_facts")
    assert len(rows) == 1
    assert rows[0]["content"] == "hello"

    # fetch_one
    row = await adapter.fetch_one("SELECT * FROM test_facts WHERE id = ?", (1,))
    assert row is not None
    assert row["content"] == "hello"

    # executemany
    await adapter.executemany("INSERT INTO test_facts (content) VALUES (?)", [("b1",), ("b2",)])
    rows = await adapter.fetch_all("SELECT COUNT(*) AS total FROM test_facts")
    assert rows[0]["total"] == 3

    # get_conn
    conn_pool = await adapter.get_conn()
    assert conn_pool is pool

    # health_check
    health = await adapter.health_check()
    assert health is True

    await adapter.close()


@pytest.mark.asyncio
async def test_router_returns_conforming_local_backend():
    """Verify that get_router().get_backend() returns a protocol-compliant StorageAdapter."""
    router = get_router()
    backend = await router.get_backend("default")

    assert isinstance(backend, StorageAdapter), (
        "Router-returned backend must satisfy StorageAdapter"
    )
    health = await backend.health_check()
    assert health is True
