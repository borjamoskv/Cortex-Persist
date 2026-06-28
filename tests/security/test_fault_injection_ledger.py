import asyncio
import os
import tempfile
import pytest
from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.database.core import connect_async_ctx, connect


@pytest.mark.asyncio
async def test_ledger_tamper_evident_corruption_detection():
    # 1. Setup secure environment
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_ledger.db")

    # 2. Initialize Ledger and write valid transactions
    async with connect_async_ctx(db_path) as conn:
        conn._conn.authorize_causal_writes()
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()

        id1 = await asyncio.wait_for(
            ledger.log_action("tenant_1", "system", "actor_1", "CREATE", "fact:1001"), timeout=5.0
        )
        id2 = await asyncio.wait_for(
            ledger.log_action("tenant_1", "system", "actor_1", "UPDATE", "fact:1001"), timeout=5.0
        )
        id3 = await asyncio.wait_for(
            ledger.log_action("tenant_1", "system", "actor_1", "DELETE", "fact:1001"), timeout=5.0
        )

        # Force flush and close
        await asyncio.sleep(0.1)
        await ledger.close()

    # 3. Verify clean state
    async with connect_async_ctx(db_path) as conn2:
        conn2._conn.authorize_causal_writes()
        ledger_verify = EnterpriseAuditLedger(conn2)
        await ledger_verify.ensure_table()
        verify_result = await ledger_verify.verify_chain()

        assert verify_result.get("status") == "verified", (
            f"Initial verification failed: {verify_result}"
        )
        await ledger_verify.close()

    # 4. Corruption Injection (Hot Physical Mutilation)
    # Internal attacker modifies the database bypassing the Ledger
    conn_sync = connect(db_path)
    conn_sync.authorize_causal_writes()
    cursor = conn_sync.cursor()

    # We change "CREATE" to "EXFILTRATE" to simulate an attack
    cursor.execute("UPDATE security_audit_log SET action = 'EXFILTRATE' WHERE audit_id = ?", (id1,))
    conn_sync.commit()
    conn_sync.close()

    # 5. Comprobar Tolerancia Bizantina
    async with connect_async_ctx(db_path) as conn3:
        conn3._conn.authorize_causal_writes()
        ledger_tampered = EnterpriseAuditLedger(conn3)
        await ledger_tampered.ensure_table()

        tampered_result = await ledger_tampered.verify_chain()

        # The system must detect the Merkle chain break or signature forgery
        assert tampered_result.get("status") == "tampered", (
            "The Ledger did not detect the physical mutilation."
        )
        assert tampered_result.get("corrupted_audit_id") == id1, (
            "The exact corrupted node was not identified."
        )
        await ledger_tampered.close()


@pytest.mark.asyncio
async def test_ledger_pinned_public_key_mismatch(monkeypatch):
    # 1. Setup secure environment
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_ledger_pinned.db")

    # 2. Initialize Ledger and write valid transactions
    async with connect_async_ctx(db_path) as conn:
        conn._conn.authorize_causal_writes()
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()

        await ledger.log_action("tenant_1", "system", "actor_1", "CREATE", "fact:1001")
        await asyncio.sleep(0.1)
        await ledger.close()

    # 3. Set a mismatched public key in environment and verify it fails with ledger_public_key_mismatch
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    
    wrong_key = ed25519.Ed25519PrivateKey.generate().public_key()
    wrong_pem = wrong_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    monkeypatch.setenv("CORTEX_LEDGER_PUBLIC_KEY", wrong_pem)
    async with connect_async_ctx(db_path) as conn2:
        conn2._conn.authorize_causal_writes()
        ledger_verify = EnterpriseAuditLedger(conn2)
        await ledger_verify.ensure_table()
        verify_result = await ledger_verify.verify_chain()

        assert verify_result.get("status") == "tampered"
        assert verify_result.get("reason") == "ledger_public_key_mismatch"
        await ledger_verify.close()

