import os

import pytest

from cortex.engine import CortexEngine
from cortex.engine.mutation_engine import MUTATION_ENGINE


@pytest.fixture(scope="function")
async def test_db():
    db_path = "test_mutation.db"
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(db_path + suffix)
        except OSError:
            pass

    engine = CortexEngine(db_path)
    await engine.init_db()
    conn = await engine.get_conn()
    yield conn
    await engine.close()

    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(db_path + suffix)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_mutation_engine_apply(test_db):
    # Insert dummy fact
    await test_db.execute(
        "INSERT INTO facts (tenant_id, project, content, fact_type, valid_from) "
        "VALUES ('default', 'test', 'Test Fact', 'knowledge', '2025-01-01T00:00:00Z')"
    )
    cursor = await test_db.execute("SELECT id FROM facts LIMIT 1")
    fact_id = (await cursor.fetchone())[0]
    await test_db.commit()

    # Apply mutation (consensus update)
    await MUTATION_ENGINE.apply(
        test_db,
        fact_id=fact_id,
        tenant_id="default",
        event_type="score_update",
        payload={"consensus_score": 1.7, "confidence": "verified"},
        signer="test",
    )

    # Verify fact updated
    cursor = await test_db.execute(
        "SELECT consensus_score, confidence FROM facts WHERE id = ?", (fact_id,)
    )
    row = await cursor.fetchone()
    assert row[0] == 1.7
    assert row[1] == "verified"

    # Verify event stored
    cursor = await test_db.execute(
        "SELECT COUNT(*) FROM entity_events WHERE entity_id = ?", (fact_id,)
    )
    count = (await cursor.fetchone())[0]
    assert count == 1
