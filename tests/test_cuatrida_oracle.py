import json
import os
import tempfile

import pytest

from cortex.database.pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine


@pytest.mark.asyncio
async def test_cuatrida_dimension_d_oracle():
    """Verify Dimension D integration (Oracle Ritual)."""
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
        # 1. Initiate Oracle Ritual
        respect = await orchestrator.oracle_ritual("test_project", "Generate Sovereign UI", 500)

        # 2. Verify metrics
        assert orchestrator.metrics.oracle_invocations == 1
        assert respect < 1.0  # Due to the heuristic
        assert respect == orchestrator.metrics.computational_respect

        # 3. Verify ledger entry
        async with engine.session() as conn:
            cursor = await conn.execute(
                "SELECT action, detail FROM transactions WHERE action = ?",
                ("cuatrida:D",)
            )
            row = await cursor.fetchone()
            assert row is not None
            detail = json.loads(row[1])
            assert detail["cost_tokens"] == 500
            assert "instant_respect" in detail

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        await pool.close()
