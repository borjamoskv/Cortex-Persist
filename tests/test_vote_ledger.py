from __future__ import annotations

import aiosqlite
import pytest

from cortex.consensus.vote_ledger import GENESIS_PREV_HASH, ImmutableVoteLedger
from cortex.migrations.mig_ledger import _migration_014_vote_ledger_refinement


async def _setup_vote_ledger_db(conn: aiosqlite.Connection) -> None:
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.execute("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            fact_type TEXT NOT NULL,
            confidence TEXT NOT NULL,
            valid_from TEXT,
            tags TEXT NOT NULL,
            source TEXT,
            metadata TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    await conn.execute(
        "INSERT INTO facts (id, tenant_id, project, content, fact_type, confidence, tags) "
        "VALUES (1, 'tenant-a', 'proj', 'fact one', 'knowledge', 'C3', '[]')"
    )
    await conn.execute(
        "INSERT INTO facts (id, tenant_id, project, content, fact_type, confidence, tags) "
        "VALUES (2, 'tenant-a', 'proj', 'fact two', 'knowledge', 'C3', '[]')"
    )
    await conn.commit()
    await conn._execute(_migration_014_vote_ledger_refinement, conn._conn)  # type: ignore[attr-defined]
    await conn.commit()


@pytest.mark.asyncio
async def test_append_vote_supports_genesis_entry() -> None:
    conn = await aiosqlite.connect(":memory:")
    try:
        await _setup_vote_ledger_db(conn)
        ledger = ImmutableVoteLedger(conn)

        entry_hash = await ledger.append_vote(1, "agent-a", "1", "tenant-a", 1.0)
        row = await (
            await conn.execute(
                "SELECT prev_hash, hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id ASC",
                ("tenant-a",),
            )
        ).fetchone()

        assert row == (GENESIS_PREV_HASH, entry_hash)
        assert await ledger.verify_chain("tenant-a") is True
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_merkle_checkpoint_matches_schema_and_detects_tampering() -> None:
    conn = await aiosqlite.connect(":memory:")
    try:
        await _setup_vote_ledger_db(conn)
        ledger = ImmutableVoteLedger(conn)

        await ledger.append_vote(1, "agent-a", "1", "tenant-a", 1.0)
        await ledger.append_vote(2, "agent-b", "-1", "tenant-a", 0.8)
        root = await ledger.checkpoint_merkle_root("tenant-a")

        checkpoint = await (
            await conn.execute(
                "SELECT root_hash, vote_start_id, vote_end_id, vote_count "
                "FROM vote_merkle_roots WHERE tenant_id = ?",
                ("tenant-a",),
            )
        ).fetchone()
        assert checkpoint == (root, 1, 2, 2)

        report = await ledger.verify_merkle_roots("tenant-a")
        assert report and report[0]["valid"] is True

        await conn.execute(
            "UPDATE vote_merkle_roots SET root_hash = ? WHERE tenant_id = ?",
            ("bogus-root", "tenant-a"),
        )
        await conn.commit()

        tampered_report = await ledger.verify_merkle_roots("tenant-a")
        assert tampered_report[0]["valid"] is False
        assert tampered_report[0]["actual"] == root
    finally:
        await conn.close()
