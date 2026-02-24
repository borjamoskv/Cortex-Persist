import json
import os
import tempfile

import pytest

from cortex.cuatrida.models import Dimension
from cortex.database.pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine


@pytest.mark.asyncio
async def test_cuatrida_ledger_hook():
    """Verify that decisions are logged to the CORTEX ledger."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Use real pool and engine for integration test
    pool = CortexConnectionPool(db_path, read_only=False)

    # Initialize schema using script execution for full DDL support
    from cortex.database.schema import ALL_SCHEMA
    async with pool.acquire() as conn:
        for statement in ALL_SCHEMA:
            await conn.executescript(statement)
        await conn.commit()

    engine = AsyncCortexEngine(pool, str(db_path))
    orchestrator = engine.cuatrida

    try:
        # 1. Log a decision via Cuatrida
        await orchestrator.log_decision(
            project="test_project",
            intent="Test decision integration",
            dimension=Dimension.TEMPORAL_SOVEREIGNTY,
            metadata={"test": "data"}
        )

        # 2. Verify ledger entry via engine.session()
        async with engine.session() as conn:
            cursor = await conn.execute(
                "SELECT action, detail FROM transactions WHERE project = ?",
                ("test_project",)
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "cuatrida:B"
            assert json.loads(row[1]) == {"test": "data"}

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        await pool.close()
