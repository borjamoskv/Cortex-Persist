# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
import aiosqlite

from babylon60.swarm.sync_protocol import SwarmSyncEngine


@pytest.fixture
async def temp_db():
    """Fixture creating a temporary database with transactions schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = await aiosqlite.connect(db_path)
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project     TEXT NOT NULL,
                action      TEXT NOT NULL,
                detail      TEXT,
                prev_hash   TEXT NOT NULL,
                hash        TEXT NOT NULL UNIQUE,
                tenant_id   TEXT NOT NULL DEFAULT "default",
                timestamp   TEXT NOT NULL
            )
        """)
        await db.commit()
    finally:
        await db.close()

    yield db_path

    # Cleanup
    try:
        Path(db_path).unlink()
    except OSError:
        pass


@pytest.mark.asyncio
async def test_swarm_sync_protocol(temp_db):
    engine = SwarmSyncEngine(db_path=temp_db)

    # 1. Verification of empty state
    genesis_proof = await engine.generate_state_proof()
    assert genesis_proof == "GENESIS"

    # 2. Inject transactions
    db = await aiosqlite.connect(temp_db)
    try:
        await db.execute(
            "INSERT INTO transactions (project, action, detail, prev_hash, hash, tenant_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("cortex", "commit", "first_tx", "GENESIS", "hash1", "default", "2026-06-30T00:00:00Z"),
        )
        await db.execute(
            "INSERT INTO transactions (project, action, detail, prev_hash, hash, tenant_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("cortex", "commit", "second_tx", "hash1", "hash2", "default", "2026-06-30T01:00:00Z"),
        )
        await db.commit()
    finally:
        await db.close()

    # 3. Verify latest hash
    latest_proof = await engine.generate_state_proof()
    assert latest_proof == "hash2"

    # 4. Get all indexed hashes
    local_hashes = await engine.get_all_indexed_hashes()
    assert local_hashes == {"hash1", "hash2"}

    # 5. Calculate delta (remote has none)
    delta_empty = await engine.calculate_delta(set())
    assert len(delta_empty) == 2
    assert delta_empty[0]["hash"] == "hash1"
    assert delta_empty[1]["hash"] == "hash2"
    assert delta_empty[0]["id"] < delta_empty[1]["id"]  # Causal ordering check

    # 6. Calculate delta (remote has hash1)
    delta_partial = await engine.calculate_delta({"hash1"})
    assert len(delta_partial) == 1
    assert delta_partial[0]["hash"] == "hash2"
