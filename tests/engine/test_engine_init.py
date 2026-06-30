# [C5-REAL] Exergy-Maximized
import pytest
import asyncio
from pathlib import Path
from babylon60.engine import CortexEngine


@pytest.mark.asyncio
async def test_engine_init_invalid_path():
    """Validates that CortexEngine raises TypeError on invalid db_path."""
    with pytest.raises(TypeError) as excinfo:
        CortexEngine(db_path=123)  # int is invalid
    assert "db_path must be str, Path, or a pool object" in str(excinfo.value)


@pytest.mark.asyncio
async def test_engine_lifecycle(tmp_path):
    """Validates the full lifecycle of CortexEngine (init, start, close)."""
    db_path = tmp_path / "lifecycle.db"

    # Create the table before initializing engine to avoid _ensure_schema_ready failure
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE cortex_meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()

    engine = CortexEngine(db_path=db_path, auto_embed=False)

    # We mock run_migrations_async but need cortex_meta table
    from unittest.mock import patch

    with (
        patch("cortex.engine.core._engine_connection.run_migrations_async"),
        patch("cortex.engine.core.cortex_engine.PersistenceSupervisor.start"),
    ):
        await engine.init_db()
        assert engine.get_connection() is not None
        # engine._schema_ready will be True because it's set after run_migrations_async
        assert engine._schema_ready is True

    # Synthesize optimization skill to avoid AttributeError on close
    engine._synthesize_skill("optimization")
    await engine.start()
    assert engine.system_state == "ACTIVE"

    await engine.close()
    assert not getattr(engine, "_conns_by_loop", {})


@pytest.mark.asyncio
async def test_engine_skill_synthesis(tmp_path):
    """Validates JIT skill synthesis."""
    db_path = tmp_path / "skills.db"
    engine = CortexEngine(db_path=db_path, auto_embed=False)

    assert "store" not in engine._skills_verified

    # Triggering a skill that uses store
    # Since we don't want to run full store (needs more setup), we can call _synthesize_skill directly
    engine._synthesize_skill("store")
    assert "store" in engine._skills_verified

    # Subsequent calls should be idempotent
    engine._synthesize_skill("store")
    assert len([s for s in engine._skills_verified if s == "store"]) == 1


@pytest.mark.asyncio
async def test_engine_session_context_manager(tmp_path):
    """Validates the engine.session() context manager."""
    db_path = tmp_path / "session.db"
    engine = CortexEngine(db_path=db_path, auto_embed=False)

    async with engine.session() as conn:
        assert conn is not None
        # Verify we can execute queries
        cursor = await conn.execute("SELECT 1")
        row = await cursor.fetchone()
        assert row[0] == 1

    await engine.close()


@pytest.mark.asyncio
async def test_engine_system_state_transitions(tmp_path):
    """Validates system state transitions and locking."""
    engine = CortexEngine(db_path=tmp_path / "state.db", auto_embed=False)
    assert engine.system_state == "ACTIVE"

    engine.set_system_state("LOCKED")
    assert engine.system_state == "LOCKED"

    engine.set_system_state("ACTIVE")
    assert engine.system_state == "ACTIVE"


@pytest.mark.asyncio
async def test_engine_aenter_aexit(tmp_path):
    """Validates AsyncContextManager interface."""
    db_path = tmp_path / "aenter.db"
    async with CortexEngine(db_path=db_path, auto_embed=False) as engine:
        await engine.init_db()
        assert engine.get_connection() is not None

    assert not getattr(engine, "_conns_by_loop", {})
