import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import aiosqlite
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from babylon60.audit.ledger import EnterpriseAuditLedger


@pytest.fixture
async def ledger_db():
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "audit.db"

    # We must mock KeyManager or ENV for the Ledger Identity to be deterministic
    os.environ["CORTEX_LEDGER_MAX_BATCH"] = "2"
    os.environ["CORTEX_TEST_ENV"] = "1"

    conn = await aiosqlite.connect(str(db_path))
    ledger = EnterpriseAuditLedger(conn)
    await ledger.ensure_table()

    yield conn, ledger, Path(temp_dir)

    await ledger.close()
    await conn.close()
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_ledger_compaction_and_verification(ledger_db):
    conn, ledger, temp_dir = ledger_db

    # Insert 10 items (5 batches if batch size is 2)
    # Wait, the anchor worker creates batches. The log_action synchronously creates individual batches if max_batch is not met?
    # Actually, log_action creates one event and triggers the anchor worker.
    # The batching logic in anchor_worker groups unanchored items by what?
    # In ledger.py, log_action creates the hash and signature IMMEDIATELY for each row!
    # So every single row is a batch of size 1, unless multiple rows are inserted in the exact same transaction before anchor worker.
    # We will just insert 10 rows sequentially.

    for i in range(10):
        await ledger.log_action(
            tenant_id="tenant_1",
            actor_role="admin",
            actor_id="user_test",
            action="CREATE",
            resource=f"file_{i}.txt",
        )
        await asyncio.sleep(0.01)  # Ensure timestamp differs

    # Let anchor worker run for a bit, but don't await the infinite loop
    await asyncio.sleep(0.1)

    # Verify pristine chain
    verify_res = await ledger.verify_chain()
    assert verify_res["status"] == "verified"
    assert verify_res["blocks"] == 10

    # Run Compaction on the first 5 rows
    snapshot_dir = temp_dir / "snapshots"
    compaction_res = await ledger.compact_ledger(max_rows=5, snapshot_dir=snapshot_dir)

    assert compaction_res["status"] == "compacted"
    assert compaction_res["rows_compacted"] == 4

    # Verify the chain again! It must still be valid.
    verify_res2 = await ledger.verify_chain()
    print("Verification result after compaction:", verify_res2)
    assert verify_res2["status"] == "verified", f"Ledger tampered: {verify_res2}"
    # We expect 7 blocks: 1 COMPACTION_NODE + 6 remaining blocks
    assert verify_res2["blocks"] == 7

    # Check SQLite row count
    async with conn.execute("SELECT COUNT(*) FROM security_audit_log") as cursor:
        count = (await cursor.fetchone())[0]
        # 10 initial - 4 deleted + 1 compaction node = 7
        assert count == 7

    # Check snapshot file exists
    snapshot_file = Path(compaction_res["snapshot_path"])
    assert snapshot_file.exists()
