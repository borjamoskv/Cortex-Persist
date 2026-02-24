import json
import os
import tempfile

import pytest

from cortex.database.pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine


@pytest.mark.asyncio
async def test_cuatrida_dimension_a_friction():
    """Verify Dimension A integration (Zero-Friction Sync)."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Use real pool and engine for integration test
    pool = CortexConnectionPool(db_path, read_only=False)

    # Initialize schema
    from cortex.database.schema import ALL_SCHEMA
    async with pool.acquire() as conn:
        for statement in ALL_SCHEMA:
            await conn.executescript(statement)
        await conn.commit()

    engine = AsyncCortexEngine(pool, str(db_path))
    orchestrator = engine.cuatrida

    try:
        # 1. Synchronize Zero-Friction State
        await orchestrator.zero_friction_sync("test_project")

        # 2. Verify metrics
        # Since ghost-control might not exist in the test env, it will be 0.0 latency
        assert orchestrator.metrics.latency_ms >= 0.0
        assert orchestrator.metrics.finitud_density > 0.0

        # 3. Verify ledger entry
        async with engine.session() as conn:
            cursor = await conn.execute(
                "SELECT action, detail FROM transactions WHERE action = ?",
                ("cuatrida:A",)
            )
            row = await cursor.fetchone()
            assert row is not None
            detail = json.loads(row[1])
            assert "latency_ms" in detail
            assert "density" in detail

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        await pool.close()
