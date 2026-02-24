import json
import os
import tempfile

import pytest

from cortex.database.pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine


@pytest.mark.asyncio
async def test_cuatrida_dimension_c_aesthetic():
    """Verify Dimension C integration (MEJORAlo)."""
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

    # Create a temporary file to scan
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("def hello():\n    pass\n")
        temp_file_path = f.name

    try:
        # 1. Validate Aesthetics
        is_honorable = await orchestrator.validate_aesthetic("test_project", temp_file_path)

        # 2. Verify metrics
        assert orchestrator.metrics.aesthetic_honor > 0
        assert is_honorable is True  # Simple file should pass 90+

        # 3. Verify ledger entry
        async with engine.session() as conn:
            cursor = await conn.execute(
                "SELECT action, detail FROM transactions WHERE action = ?",
                ("cuatrida:C",)
            )
            row = await cursor.fetchone()
            assert row is not None
            detail = json.loads(row[1])
            assert detail["score"] > 0
            assert detail["honorable"] is True

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        await pool.close()
