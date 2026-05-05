from __future__ import annotations

import pytest

from cortex.database.pool import CortexConnectionPool
from cortex.database.schema import get_all_schema
from cortex.engine import CortexEngine
from cortex.utils.canonical import canonical_json, compute_tx_hash, now_iso


@pytest.fixture
async def ledger_engine(tmp_path):
    db_path = str(tmp_path / "tenant-hash-binding.db")
    pool = CortexConnectionPool(db_path, read_only=False)
    await pool.initialize()
    async with pool.acquire() as conn:
        for sql in get_all_schema():
            if "USING vec0" in sql:
                continue
            await conn.executescript(sql)
        await conn.commit()
    engine = CortexEngine(pool, db_path)
    yield engine
    await pool.close()


@pytest.mark.asyncio
async def test_new_transaction_hash_detects_tenant_transplant(ledger_engine) -> None:
    async with ledger_engine.session() as conn:
        tx_id = await ledger_engine._log_transaction(
            conn,
            "ledger-test",
            "store",
            {"fact_id": 1},
            tenant_id="tenant-alpha",
        )
        await conn.commit()

        await conn.execute("DROP TRIGGER IF EXISTS prevent_tx_update")
        await conn.execute(
            "UPDATE transactions SET tenant_id = ? WHERE id = ?",
            ("tenant-beta", tx_id),
        )
        await conn.commit()

    report = await ledger_engine.verify_ledger(tenant_id="tenant-beta")

    assert report["valid"] is False
    assert any(v["type"] == "TAMPER_DETECTED" for v in report["violations"])


@pytest.mark.asyncio
async def test_legacy_v2_transaction_hash_remains_verifiable(ledger_engine) -> None:
    detail_json = canonical_json({"fact_id": 1})
    timestamp = now_iso()
    legacy_hash = compute_tx_hash(
        "GENESIS",
        "ledger-test",
        "store",
        detail_json,
        timestamp,
    )

    async with ledger_engine.session() as conn:
        await conn.execute(
            "INSERT INTO transactions "
            "(tenant_id, project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "tenant-alpha",
                "ledger-test",
                "store",
                detail_json,
                "GENESIS",
                legacy_hash,
                timestamp,
            ),
        )
        await conn.commit()

    report = await ledger_engine.verify_ledger(tenant_id="tenant-alpha")

    assert report["valid"] is True
    assert report["tx_checked"] == 1
