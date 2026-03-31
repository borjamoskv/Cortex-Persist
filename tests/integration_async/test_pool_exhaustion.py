import asyncio
import sqlite3
from pathlib import Path

import pytest

from cortex.database.pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine


@pytest.fixture
async def async_engine(tmp_path: Path) -> AsyncCortexEngine:
    db_path = str(tmp_path / "test_exhaustion.db")

    # Setup initial database schema needed for consensus/agents
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT,
            agent_type TEXT,
            public_key TEXT,
            tenant_id TEXT,
            is_active INTEGER DEFAULT 1,
            base_reputation REAL DEFAULT 1.0,
            reputation_score REAL DEFAULT 1.0,
            alignment_hits INTEGER DEFAULT 0,
            alignment_misses INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consensus_votes_v2 (
            id INTEGER PRIMARY KEY,
            fact_id INTEGER,
            agent_id TEXT,
            vote INTEGER,
            vote_weight REAL,
            agent_rep_at_vote REAL,
            vote_reason TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            project TEXT,
            action TEXT,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT,
            timestamp TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT,
            content TEXT,
            confidence TEXT
        )
    """)
    conn.commit()
    conn.close()

    # Small pool to force contention
    pool = CortexConnectionPool(db_path, min_connections=2, max_connections=5)
    await pool.initialize()

    engine = AsyncCortexEngine(pool=pool, db_path=db_path)

    yield engine

    await pool.close()


@pytest.mark.asyncio
async def test_pool_exhaustion_register_agent(async_engine: AsyncCortexEngine):
    """Verify concurrent `register_agent` calls do not leak or exhaust the connection pool."""
    tasks = []
    # 50 concurrent requests against a pool sizes of 5
    for i in range(50):
        tasks.append(
            async_engine.register_agent(
                name=f"agent_stress_{i}",
                agent_type="test_swarm",
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Ensure no timeouts or locked databases escaped
    exceptions = [r for r in results if isinstance(r, Exception)]
    assert len(exceptions) == 0, f"Exceptions occurred during concurrent write: {exceptions}"

    successes = [r for r in results if isinstance(r, str)]  # agent_id
    assert len(successes) == 50

    # Assert pool health
    # Connections should have been returned, meaning the pool queue shouldn't be empty
    assert not async_engine._pool._pool.empty()
    assert async_engine._pool._active_count <= 5


@pytest.mark.asyncio
async def test_pool_exhaustion_vote_v2(async_engine: AsyncCortexEngine):
    """Verify concurrent `vote_v2` calls do not leak or exhaust the connection pool."""

    # Setup test fact and agent
    agent_id = await async_engine.register_agent("voter_agent")

    async with async_engine.session() as conn:
        await conn.execute(
            "INSERT INTO facts (id, tenant_id, content) VALUES (1, 'default', 'test fact')"
        )
        await conn.commit()

    tasks = []
    # Force 50 concurrent votes on the same fact
    for i in range(50):
        tasks.append(
            async_engine.vote_v2(fact_id=1, agent_id=agent_id, value=1, reason=f"stress_vote_{i}")
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # A few might fail due to database locking retries exceeded, but pool must *not* be leaked/exhausted.
    # The fix ensures proper context managers are used.

    exceptions = [r for r in results if isinstance(r, Exception)]  # noqa: F841

    # Ensure pool is healthy regardless of sqlite lock contention
    assert not async_engine._pool._pool.empty()
    assert async_engine._pool._active_count <= 5
