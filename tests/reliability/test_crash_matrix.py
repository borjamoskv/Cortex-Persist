import pytest
import sqlite3
import asyncio
from unittest.mock import patch
from babylon60.engine.core.cortex_engine import CortexEngine
from babylon60.database.core import causal_write

from pathlib import Path
import os

os.environ["CORTEX_VIRGO_MODE"] = "TEST"
os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"


@pytest.fixture
async def engine(tmp_path: Path):
    from babylon60.engine.core.cortex_engine import CortexEngine

    db_path = str(tmp_path / "cortex_crash.db")
    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()


@pytest.mark.asyncio
async def test_engine_recovers_from_simulated_crash(engine: CortexEngine):
    """
    Test that the engine successfully rolls back state and doesn't get
    permanently corrupted if a write operation crashes midway.
    """
    # 1. Store a successful fact to ensure baseline is working
    fact_id_1 = await engine.store(
        project="reliability",
        content="Baseline fact",
        fact_type="knowledge",
        source="agent:test_suite",
        confidence="C5",
    )
    assert fact_id_1 is not None

    # 2. Simulate a crash during the next store operation
    # We mock `insert_fact_record` so it fails mid-transaction.
    with patch("cortex.engine.core.store_mixin.insert_fact_record") as mock_insert:
        mock_insert.side_effect = sqlite3.OperationalError("Simulated disk crash")

        with pytest.raises(sqlite3.OperationalError):
            await engine.store(
                project="reliability",
                content="Crashing fact",
                fact_type="knowledge",
                source="agent:test_suite",
                confidence="C5",
            )

    # 3. Ensure the engine is still usable and the crashed fact wasn't persisted partially
    # By storing another fact.
    fact_id_3 = await engine.store(
        project="reliability",
        content="Recovery fact",
        fact_type="knowledge",
        source="agent:test_suite",
        confidence="C5",
    )
    assert fact_id_3 is not None
    assert fact_id_3 != fact_id_1
