"""
CORTEX v6.0 — PostgreSQL Backend Integration Tests.

These tests require a running PostgreSQL instance.
Set POSTGRES_DSN env var to run them, otherwise they are skipped.

Usage:
    # Start PostgreSQL via Docker:
    docker run -d --name cortex-pg \
        -e POSTGRES_PASSWORD=$TEST_PG_PASS \
        -e POSTGRES_DB=cortex_test -p 5433:5432 postgres:16-alpine

    # Run tests:
    POSTGRES_DSN=postgresql://postgres:$TEST_PG_PASS@localhost:5433/cortex_test \
        pytest tests/test_postgres_backend.py -v
"""

from __future__ import annotations

import os

import pytest

# Skip entire module if no PostgreSQL available
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "")
pytestmark = pytest.mark.skipif(
    not POSTGRES_DSN,
    reason="POSTGRES_DSN not set — skip PostgreSQL integration tests",
)


@pytest.fixture
async def pg_backend():
    """Create and connect a PostgresBackend for testing."""
    from cortex.storage.postgres import PostgresBackend

    backend = PostgresBackend(dsn=POSTGRES_DSN, min_size=1, max_size=3)
    await backend.connect()
    yield backend
    # Cleanup: drop test tables
    try:
        await backend.execute("DROP TABLE IF EXISTS _test_pg CASCADE")
    except Exception:
        pass
    await backend.close()


@pytest.mark.asyncio
async def test_connect_and_health_check(pg_backend):
    """Backend should connect and pass health check."""
    assert await pg_backend.health_check() is True


@pytest.mark.asyncio
async def test_execute_select(pg_backend):
    """Execute a simple SELECT."""
    rows = await pg_backend.execute("SELECT 1 AS value, 'hello' AS msg")
    assert len(rows) == 1
    assert rows[0]["value"] == 1
    assert rows[0]["msg"] == "hello"


@pytest.mark.asyncio
async def test_execute_insert_and_return_id(pg_backend):
    """INSERT should return the generated id."""
    # Create test table
    await pg_backend.executescript(
        "CREATE TABLE IF NOT EXISTS _test_pg ("
        "  id BIGSERIAL PRIMARY KEY,"
        "  content TEXT NOT NULL,"
        "  created_at TIMESTAMPTZ DEFAULT NOW()"
        ")"
    )

    row_id = await pg_backend.execute_insert(
        "INSERT INTO _test_pg (content) VALUES ($1)",
        ("test_fact",),
    )
    assert row_id > 0

    # Verify the row exists
    rows = await pg_backend.execute(
        "SELECT id, content FROM _test_pg WHERE id = $1",
        (row_id,),
    )
    assert len(rows) == 1
    assert rows[0]["content"] == "test_fact"


@pytest.mark.asyncio
async def test_param_translation(pg_backend):
    """SQLite-style ? params should be auto-translated to $N."""
    await pg_backend.executescript(
        "CREATE TABLE IF NOT EXISTS _test_pg (  id BIGSERIAL PRIMARY KEY,  content TEXT NOT NULL)"
    )

    # Use ? style params (SQLite compat)
    row_id = await pg_backend.execute_insert(
        "INSERT INTO _test_pg (content) VALUES (?)",
        ("param_test",),
    )
    assert row_id > 0

    # Verify
    rows = await pg_backend.execute(
        "SELECT content FROM _test_pg WHERE id = ?",
        (row_id,),
    )
    assert len(rows) == 1
    assert rows[0]["content"] == "param_test"


@pytest.mark.asyncio
async def test_executemany(pg_backend):
    """Batch insert with executemany."""
    await pg_backend.executescript(
        "CREATE TABLE IF NOT EXISTS _test_pg (  id BIGSERIAL PRIMARY KEY,  value TEXT NOT NULL)"
    )

    params = [("item_1",), ("item_2",), ("item_3",)]
    await pg_backend.executemany(
        "INSERT INTO _test_pg (value) VALUES ($1)",
        params,
    )

    rows = await pg_backend.execute("SELECT value FROM _test_pg ORDER BY id")
    assert len(rows) == 3
    assert [r["value"] for r in rows] == ["item_1", "item_2", "item_3"]


@pytest.mark.asyncio
async def test_executemany_empty(pg_backend):
    """executemany with empty list should be a no-op."""
    await pg_backend.executemany("INSERT INTO nonexistent (x) VALUES ($1)", [])


@pytest.mark.asyncio
async def test_executescript(pg_backend):
    """Execute multi-statement script."""
    await pg_backend.executescript("""
        CREATE TABLE IF NOT EXISTS _test_pg (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL
        );
        INSERT INTO _test_pg (name) VALUES ('script_test');
    """)

    rows = await pg_backend.execute("SELECT name FROM _test_pg")
    assert any(r["name"] == "script_test" for r in rows)


@pytest.mark.asyncio
async def test_close_and_reconnect(pg_backend):
    """After close, health_check should fail."""
    await pg_backend.close()
    assert await pg_backend.health_check() is False


@pytest.mark.asyncio
async def test_dsn_sanitize():
    """Sensitive parts of DSN should be hidden in repr."""
    from cortex.storage.postgres import PostgresBackend

    backend = PostgresBackend(
        dsn="postgresql://admin:s3cret@db.cloud.com:5432/cortex"  # noqa: S105
    )
    r = repr(backend)
    assert "supersecret" not in r
    assert "***" in r
    assert "admin" in r


@pytest.mark.asyncio
async def test_schema_initialization(pg_backend):
    """Full PG schema should apply without errors."""
    from cortex.storage.pg_schema import PG_ALL_SCHEMA, PG_EXTENSIONS

    # Apply extensions (may fail if not superuser, that's OK)
    try:
        await pg_backend.executescript(PG_EXTENSIONS)
    except Exception:
        pytest.skip("pgvector/pg_trgm extensions not available")

    # Apply all schema
    for schema_sql in PG_ALL_SCHEMA:
        await pg_backend.executescript(schema_sql)

    # Verify core table exists
    rows = await pg_backend.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'facts'"
    )
    assert len(rows) == 1
