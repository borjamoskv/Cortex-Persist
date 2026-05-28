"""Tests for cortex.database.pool.CortexConnectionPool."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cortex.database.pool import CortexConnectionPool


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Create a temp SQLite database with WAL mode."""
    db = str(tmp_path / "test_pool.db")
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS probe (id INTEGER PRIMARY KEY, val TEXT)")
    conn.commit()
    conn.close()
    return db


@pytest.fixture
async def pool(db_path: str):
    """Provide an initialized pool, close after test."""
    p = CortexConnectionPool(db_path, min_connections=2, max_connections=5)
    await p.initialize()
    yield p
    await p.close()


# ─── Initialization ──────────────────────────────────────────────────


class TestInitialization:
    async def test_initialize_sets_flag(self, pool: CortexConnectionPool):
        assert pool._initialized is True

    async def test_double_initialize_is_idempotent(self, pool: CortexConnectionPool):
        await pool.initialize()  # Should not raise
        assert pool._initialized is True

    async def test_pre_warm_creates_min_connections(self, pool: CortexConnectionPool):
        assert pool._active_count >= pool.min_connections


# ─── Acquire / Release ────────────────────────────────────────────────


class TestAcquire:
    async def test_acquire_returns_healthy_connection(self, pool: CortexConnectionPool):
        async with pool.acquire() as conn:
            async with conn.execute("SELECT 1") as cursor:
                row = await cursor.fetchone()
                assert row[0] == 1

    async def test_acquire_multiple_connections(self, pool: CortexConnectionPool):
        """Acquire several connections concurrently."""
        import asyncio

        async def use_conn():
            async with pool.acquire() as conn:
                async with conn.execute("SELECT 1") as cursor:
                    await cursor.fetchone()

        await asyncio.gather(*[use_conn() for _ in range(5)])

    async def test_connection_returned_to_pool(self, pool: CortexConnectionPool):
        """After release, pool should be non-empty."""
        async with pool.acquire() as _conn:
            pass
        assert not pool._pool.empty()


# ─── Health Checks ────────────────────────────────────────────────────


class TestHealthCheck:
    async def test_healthy_connection_passes(self, pool: CortexConnectionPool):
        async with pool.acquire() as conn:
            assert await pool._is_healthy(conn) is True


# ─── Close ────────────────────────────────────────────────────────────


class TestClose:
    async def test_close_drains_pool(self, db_path: str):
        p = CortexConnectionPool(db_path, min_connections=3, max_connections=5)
        await p.initialize()
        await p.close()
        assert p._pool.empty()
        assert p._initialized is False

    async def test_close_without_init_is_safe(self, db_path: str):
        p = CortexConnectionPool(db_path)
        await p.close()  # Should not raise


# ─── Auto-initialization on acquire ──────────────────────────────────


class TestAutoInit:
    async def test_acquire_auto_initializes(self, db_path: str):
        p = CortexConnectionPool(db_path, min_connections=1, max_connections=3)
        assert p._initialized is False
        async with p.acquire() as conn:
            async with conn.execute("SELECT 1") as cursor:
                row = await cursor.fetchone()
                assert row[0] == 1
        assert p._initialized is True
        await p.close()
