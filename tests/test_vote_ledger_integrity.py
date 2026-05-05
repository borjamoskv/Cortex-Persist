import hashlib

import aiosqlite
import pytest

from cortex.consensus.vote_ledger import ImmutableVoteLedger
from cortex.database.schema import get_all_schema


async def _init_db(db_path) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(db_path)
    for sql in get_all_schema():
        if "USING vec0" in sql:
            continue
        await conn.executescript(sql)
    await conn.commit()
    return conn


@pytest.mark.asyncio
async def test_vote_ledger_hash_chain_and_merkle_roots_are_recomputed(tmp_path):
    conn = await _init_db(tmp_path / "vote-ledger.db")
    try:
        fact_hash = hashlib.sha256(b"ledger-bound fact").hexdigest()
        await conn.execute(
            "INSERT INTO facts (id, tenant_id, project, content, hash) VALUES (?, ?, ?, ?, ?)",
            (1, "tenant-a", "audit", "ledger-bound fact", fact_hash),
        )
        await conn.commit()

        ledger = ImmutableVoteLedger(conn)
        first_hash = await ledger.append_vote(1, "agent-a", 1, "tenant-a")
        second_hash = await ledger.append_vote(1, "agent-b", -1, "tenant-a")

        cursor = await conn.execute(
            "SELECT prev_hash, hash, fact_hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id",
            ("tenant-a",),
        )
        rows = await cursor.fetchall()
        assert rows == [("GENESIS", first_hash, fact_hash), (first_hash, second_hash, fact_hash)]

        root = await ledger.create_checkpoint("tenant-a")
        assert root
        assert await ledger.verify_merkle_roots("tenant-a") == [
            {
                "checkpoint_id": 1,
                "valid": True,
                "expected": root,
                "actual": root,
                "vote_start_id": 1,
                "vote_end_id": 2,
                "vote_count": 2,
            }
        ]

        await conn.execute(
            "UPDATE vote_merkle_roots SET root_hash = ? WHERE tenant_id = ?",
            ("tampered-root", "tenant-a"),
        )
        await conn.commit()

        merkle_report = await ledger.verify_merkle_roots("tenant-a")
        assert merkle_report[0]["valid"] is False
        assert merkle_report[0]["actual"] == root
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_vote_ledger_detects_fact_hash_drift(tmp_path):
    conn = await _init_db(tmp_path / "fact-drift.db")
    try:
        fact_hash = hashlib.sha256(b"original fact").hexdigest()
        await conn.execute(
            "INSERT INTO facts (id, tenant_id, project, content, hash) VALUES (?, ?, ?, ?, ?)",
            (1, "tenant-a", "audit", "original fact", fact_hash),
        )
        await conn.commit()

        ledger = ImmutableVoteLedger(conn)
        await ledger.append_vote(1, "agent-a", 1, "tenant-a")

        await conn.execute(
            "UPDATE facts SET hash = ? WHERE id = ? AND tenant_id = ?",
            (hashlib.sha256(b"mutated fact").hexdigest(), 1, "tenant-a"),
        )
        await conn.commit()

        report = await ledger.verify_chain_integrity("tenant-a")
        assert report["valid"] is False
        assert {violation["type"] for violation in report["violations"]} == {
            "fact_hash_mismatch"
        }
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_vote_ledger_rejects_unhashed_facts(tmp_path):
    conn = await _init_db(tmp_path / "missing-hash.db")
    try:
        await conn.execute(
            "INSERT INTO facts (id, tenant_id, project, content) VALUES (?, ?, ?, ?)",
            (1, "tenant-a", "audit", "unhashed fact"),
        )
        await conn.commit()

        ledger = ImmutableVoteLedger(conn)
        with pytest.raises(ValueError, match="has no hash"):
            await ledger.append_vote(1, "agent-a", 1, "tenant-a")
    finally:
        await conn.close()
