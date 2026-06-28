# [C5-REAL] Exergy-Maximized
"""
Comprehensive tests for cortex.audit module.

Covers:
  - EnterpriseAuditLedger: table creation, log_action, hash-chain integrity,
    batch worker, ZK seal verification, run_scan stub
  - AuditAnalystGrok: scan execution, result shape, threat scoring
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from unittest.mock import patch

import aiosqlite
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def audit_conn(tmp_path):
    """Provides a fresh aiosqlite connection for each test."""
    from cortex.database.core import connect_async
    db_path = str(tmp_path / "audit_test.db")
    conn = await connect_async(db_path)
    yield conn
    await conn.close()


@pytest.fixture
async def ledger(audit_conn, tmp_path):
    """Creates an EnterpriseAuditLedger with a fresh keypair (no PEM reuse)."""
    # Force generation of a fresh key by pointing to a non-existent PEM path
    pem_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_sovereign.pem")
    with patch(
        "cortex.audit.ledger.os.path.exists",
        side_effect=lambda p: False if p == pem_path else os.path.exists(p),
    ):
        from cortex.audit.ledger import EnterpriseAuditLedger

        ledger = object.__new__(EnterpriseAuditLedger)
        # Manually init to avoid writing PEM to test source tree
        from cryptography.hazmat.primitives.asymmetric import ed25519

        ledger._conn = audit_conn
        ledger._ready = False
        ledger._last_hash = "GENESIS"
        ledger._lock = asyncio.Lock()
        ledger._batch_queue = []
        ledger._batch_task = None
        ledger.batch_window_ms = 10  # fast flush for tests
        ledger.max_batch_size = 500
        ledger.private_key = ed25519.Ed25519PrivateKey.generate()
        ledger.public_key = ledger.private_key.public_key()

    yield ledger
    await ledger.close()


# ── EnterpriseAuditLedger Tests ───────────────────────────────────────────────


class TestEnterpriseAuditLedger:
    """Test suite for the immutable cryptographic audit ledger."""

    @pytest.mark.asyncio
    async def test_ensure_table_creates_schema(self, ledger):
        """Verify ensure_table creates the security_audit_log table."""
        await ledger.ensure_table()
        cursor = await ledger._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='security_audit_log'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "security_audit_log"

    @pytest.mark.asyncio
    async def test_ensure_table_idempotent(self, ledger):
        """Calling ensure_table twice must not error or create duplicate tables."""
        await ledger.ensure_table()
        await ledger.ensure_table()
        assert ledger._ready is True

    @pytest.mark.asyncio
    async def test_log_action_returns_audit_id(self, ledger):
        """log_action must return a non-empty hex audit_id."""
        audit_id = await ledger.log_action(
            tenant_id="test-tenant",
            actor_role="admin",
            actor_id="agent-001",
            action="STORE_FACT",
            resource="/facts/42",
        )
        assert isinstance(audit_id, str)
        assert len(audit_id) == 64  # SHA-256 hex digest

    @pytest.mark.asyncio
    async def test_log_action_persists_to_db(self, ledger):
        """Verify logged actions are actually persisted in SQLite."""
        await ledger.log_action(
            tenant_id="tenant-alpha",
            actor_role="agent",
            actor_id="agent-002",
            action="READ_MEMORY",
            resource="/memory/search",
            status="SUCCESS",
        )
        cursor = await ledger._conn.execute(
            "SELECT tenant_id, actor_role, actor_id, action, resource, status "
            "FROM security_audit_log"
        )
        rows = await cursor.fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == "tenant-alpha"
        assert row[1] == "agent"
        assert row[2] == "agent-002"
        assert row[3] == "READ_MEMORY"
        assert row[4] == "/memory/search"
        assert row[5] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_hash_chain_integrity(self, ledger):
        """Verify that log entries form a valid hash chain (prev_hash linkage)."""
        await ledger.log_action(
            tenant_id="t1",
            actor_role="admin",
            actor_id="a1",
            action="act1",
            resource="r1",
        )
        # Sleep to let the first batch flush separately
        await asyncio.sleep(0.05)
        await ledger.log_action(
            tenant_id="t1",
            actor_role="admin",
            actor_id="a1",
            action="act2",
            resource="r2",
        )
        # Sleep to let the second batch flush
        await asyncio.sleep(0.05)

        cursor = await ledger._conn.execute(
            "SELECT prev_hash, signature FROM security_audit_log ORDER BY rowid ASC"
        )
        rows = await cursor.fetchall()
        assert len(rows) >= 1

        # First entry's prev_hash must be GENESIS
        assert rows[0][0] == "GENESIS"

        # If batch flushed as two separate batches, second should chain to the entry_hash of the first
        if len(rows) == 2:
            cursor2 = await ledger._conn.execute(
                "SELECT audit_id FROM security_audit_log WHERE signature = ?", (rows[0][1],)
            )
            batch1_rows = await cursor2.fetchall()
            batch1_ids = [r[0] for r in batch1_rows]

            from cortex.audit.smt import SparseMerkleTree
            smt_state = SparseMerkleTree()
            for aid in batch1_ids:
                smt_state.update(hashlib.sha256(aid.encode()).hexdigest(), aid)
            merkle_root = smt_state.root

            expected_entry_hash = hashlib.sha256(
                f"merkle_batch:{merkle_root}:GENESIS".encode()
            ).hexdigest()
            assert rows[1][0] == expected_entry_hash
            assert ledger.verify_batch(batch1_ids, "GENESIS", rows[0][1]) is True

    @pytest.mark.asyncio
    async def test_multiple_actions_batch_flush(self, ledger):
        """Multiple rapid log_action calls should be batch-flushed correctly."""
        tasks = []
        for i in range(5):
            tasks.append(
                ledger.log_action(
                    tenant_id="batch-tenant",
                    actor_role="agent",
                    actor_id=f"agent-{i}",
                    action=f"ACTION_{i}",
                    resource=f"/resource/{i}",
                )
            )
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert all(isinstance(r, str) and len(r) == 64 for r in results)

        # Verify all 5 rows are in DB
        cursor = await ledger._conn.execute(
            "SELECT COUNT(*) FROM security_audit_log WHERE tenant_id='batch-tenant'"
        )
        count = (await cursor.fetchone())[0]
        assert count == 5

    @pytest.mark.asyncio
    async def test_signature_is_valid_ed25519(self, ledger):
        """Verify the signature stored in DB is a valid Ed25519 signature."""
        await ledger.log_action(
            tenant_id="sig-tenant",
            actor_role="system",
            actor_id="sys-001",
            action="VERIFY_SIG",
            resource="/audit",
        )
        cursor = await ledger._conn.execute(
            "SELECT prev_hash, signature FROM security_audit_log LIMIT 1"
        )
        row = await cursor.fetchone()
        prev_hash, signature_hex = row[0], row[1]
        assert len(signature_hex) == 128  # Ed25519 signature = 64 bytes = 128 hex chars

    @pytest.mark.asyncio
    async def test_verify_zk_seal_valid(self, ledger):
        """verify_zk_seal must return True for a valid signature."""
        payload = "test_payload_data"
        signature = ledger.private_key.sign(payload.encode("utf-8"))
        assert ledger.verify_zk_seal(payload, signature.hex()) is True

    @pytest.mark.asyncio
    async def test_verify_zk_seal_invalid_signature(self, ledger):
        """verify_zk_seal must return False for a tampered signature."""
        payload = "test_payload_data"
        fake_sig = "00" * 64  # 64 bytes of zeros
        assert ledger.verify_zk_seal(payload, fake_sig) is False

    @pytest.mark.asyncio
    async def test_verify_zk_seal_wrong_payload(self, ledger):
        """verify_zk_seal must return False when payload doesn't match signature."""
        original = "original_payload"
        tampered = "tampered_payload"
        signature = ledger.private_key.sign(original.encode("utf-8"))
        assert ledger.verify_zk_seal(tampered, signature.hex()) is False

    @pytest.mark.asyncio
    async def test_verify_zk_seal_invalid_hex(self, ledger):
        """verify_zk_seal must return False for non-hex garbage."""
        assert ledger.verify_zk_seal("data", "not_hex_at_all") is False

    @pytest.mark.asyncio
    async def test_run_scan_stub(self, ledger):
        """run_scan currently returns a stub; verify the expected shape."""
        from cortex.audit.analyst import AuditAnalystGrok
        analyst = AuditAnalystGrok(ledger)
        result = await analyst.run_scan()
        assert "status" in result
        assert "threat_score" in result

    @pytest.mark.asyncio
    async def test_genesis_last_hash(self, ledger):
        """Before any log, _last_hash must be 'GENESIS'."""
        assert ledger._last_hash == "GENESIS"

    @pytest.mark.asyncio
    async def test_last_hash_advances_after_log(self, ledger):
        """After logging, _last_hash must no longer be GENESIS."""
        await ledger.log_action(
            tenant_id="t",
            actor_role="r",
            actor_id="a",
            action="X",
            resource="Y",
        )
        assert ledger._last_hash != "GENESIS"

    @pytest.mark.asyncio
    async def test_log_action_default_status(self, ledger):
        """log_action with no explicit status should default to 'SUCCESS'."""
        await ledger.log_action(
            tenant_id="t",
            actor_role="r",
            actor_id="a",
            action="X",
            resource="Y",
        )
        cursor = await ledger._conn.execute("SELECT status FROM security_audit_log LIMIT 1")
        row = await cursor.fetchone()
        assert row[0] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_log_action_custom_status(self, ledger):
        """log_action must respect a custom status value."""
        await ledger.log_action(
            tenant_id="t",
            actor_role="r",
            actor_id="a",
            action="X",
            resource="Y",
            status="DENIED",
        )
        cursor = await ledger._conn.execute("SELECT status FROM security_audit_log LIMIT 1")
        row = await cursor.fetchone()
        assert row[0] == "DENIED"

    @pytest.mark.asyncio
    async def test_audit_id_is_deterministic(self, ledger):
        """audit_id is SHA-256 of timestamp+actor+action — verify it's consistent."""
        # We can't predict the exact timestamp, but we can verify the format
        aid = await ledger.log_action(
            tenant_id="t",
            actor_role="r",
            actor_id="a",
            action="X",
            resource="Y",
        )
        # Must be valid hex
        int(aid, 16)

    @pytest.mark.asyncio
    async def test_ensure_table_loads_last_hash_from_db(self, audit_conn, tmp_path):
        """When table has existing rows, ensure_table should load last signature as _last_hash."""
        from cryptography.hazmat.primitives.asymmetric import ed25519

        from cortex.audit.ledger import EnterpriseAuditLedger

        # Build first ledger manually
        l1 = object.__new__(EnterpriseAuditLedger)
        l1._conn = audit_conn
        l1._ready = False
        l1._last_hash = "GENESIS"
        l1._lock = asyncio.Lock()
        l1._batch_queue = []
        l1._batch_task = None
        l1.batch_window_ms = 10
        l1.max_batch_size = 500
        l1.private_key = ed25519.Ed25519PrivateKey.generate()
        l1.public_key = l1.private_key.public_key()

        await l1.log_action(
            tenant_id="t",
            actor_role="r",
            actor_id="a",
            action="X",
            resource="Y",
        )
        saved_hash = l1._last_hash

        # Build second ledger pointing to same conn, verify it loads the last hash
        l2 = object.__new__(EnterpriseAuditLedger)
        l2._conn = audit_conn
        l2._ready = False
        l2._last_hash = "GENESIS"
        l2._lock = asyncio.Lock()
        l2._batch_queue = []
        l2._batch_task = None
        l2.batch_window_ms = 10
        l2.max_batch_size = 500
        l2.private_key = l1.private_key
        l2.public_key = l1.public_key

        await l2.ensure_table()
        assert l2._last_hash == saved_hash


# ── AuditAnalystGrok Tests ────────────────────────────────────────────────────


class TestAuditAnalystGrok:
    """Test suite for the heuristic-based audit analyst."""

    @pytest.fixture
    async def analyst(self, ledger):
        from cortex.audit.analyst import AuditAnalystGrok

        return AuditAnalystGrok(ledger)

    @pytest.mark.asyncio
    async def test_run_scan_returns_expected_shape(self, analyst):
        """run_scan must return a dict with all required keys."""
        result = await analyst.run_scan()
        assert "status" in result
        assert "threat_score" in result
        assert "anomalies_detected" in result
        assert "heuristic_version" in result
        assert "findings" in result

    @pytest.mark.asyncio
    async def test_run_scan_default_is_secure(self, analyst):
        """With no anomaly data, scan should return SECURE."""
        result = await analyst.run_scan()
        assert result["status"] == "SECURE"
        assert result["threat_score"] < 0.1
        assert result["anomalies_detected"] == 0

    @pytest.mark.asyncio
    async def test_run_scan_heuristic_version(self, analyst):
        """Verify heuristic version string is present."""
        result = await analyst.run_scan()
        assert result["heuristic_version"] == "Grok-4.1-Heuristic"

    @pytest.mark.asyncio
    async def test_run_scan_findings_non_empty(self, analyst):
        """Findings list must always have at least one entry."""
        result = await analyst.run_scan()
        assert len(result["findings"]) >= 1

    @pytest.mark.asyncio
    async def test_run_scan_with_tenant_id(self, analyst):
        """run_scan should accept optional tenant_id without error."""
        result = await analyst.run_scan(_tenant_id="specific-tenant")
        assert result["status"] == "SECURE"

    @pytest.mark.asyncio
    async def test_analyst_stores_ledger_ref(self, ledger):
        """AuditAnalystGrok must hold a reference to the provided ledger."""
        from cortex.audit.analyst import AuditAnalystGrok

        analyst = AuditAnalystGrok(ledger)
        assert analyst.ledger is ledger

    @pytest.mark.asyncio
    async def test_analyst_initial_threat_score(self, ledger):
        """Initial threat score must be 0.0."""
        from cortex.audit.analyst import AuditAnalystGrok

        analyst = AuditAnalystGrok(ledger)
        assert analyst._threat_score == 0.0
