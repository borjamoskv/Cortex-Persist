"""Tests for per-tenant hash chain isolation in SovereignLedger.

Validates that:
1. Each tenant gets an independent hash chain starting from GENESIS.
2. Transactions from tenant_a do not contaminate tenant_b's chain.
3. Integrity audit correctly scopes per-tenant.
4. The sync record_transaction path also scopes by tenant_id.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest
import aiosqlite

from cortex.ledger.ledger_core import SovereignLedger


@pytest.fixture
def sync_db():
    """Create a temporary SQLite database with sync connection."""
    fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fd.close()
    conn = sqlite3.connect(fd.name)
    yield conn
    conn.close()
    Path(fd.name).unlink(missing_ok=True)


@pytest.fixture
async def async_db():
    """Create a temporary async SQLite database."""
    fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fd.close()
    conn = await aiosqlite.connect(fd.name)
    yield conn
    await conn.close()
    Path(fd.name).unlink(missing_ok=True)


class TestSyncTenantScoping:
    """Test tenant isolation on the synchronous record_transaction path."""

    def test_default_tenant_chain(self, sync_db):
        """Default tenant starts from GENESIS."""
        ledger = SovereignLedger(sync_db)
        h1 = ledger.record_transaction("proj", "store", {"key": "v1"})
        h2 = ledger.record_transaction("proj", "store", {"key": "v2"})

        # Verify chain: h2 should reference h1
        cursor = sync_db.execute(
            "SELECT prev_hash, hash FROM transactions ORDER BY id"
        )
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "GENESIS"  # First tx chains from GENESIS
        assert rows[1][0] == rows[0][1]  # Second tx chains from first

    def test_multi_tenant_independent_chains(self, sync_db):
        """Two tenants get independent GENESIS starts."""
        ledger = SovereignLedger(sync_db)

        h_a1 = ledger.record_transaction(
            "proj", "store", {"t": "a1"}, tenant_id="tenant_a"
        )
        h_b1 = ledger.record_transaction(
            "proj", "store", {"t": "b1"}, tenant_id="tenant_b"
        )
        h_a2 = ledger.record_transaction(
            "proj", "store", {"t": "a2"}, tenant_id="tenant_a"
        )

        # Verify tenant_a chain
        cursor = sync_db.execute(
            "SELECT prev_hash, hash FROM transactions "
            "WHERE tenant_id = ? ORDER BY id",
            ("tenant_a",),
        )
        a_rows = cursor.fetchall()
        assert len(a_rows) == 2
        assert a_rows[0][0] == "GENESIS"
        assert a_rows[1][0] == a_rows[0][1]

        # Verify tenant_b chain
        cursor = sync_db.execute(
            "SELECT prev_hash, hash FROM transactions "
            "WHERE tenant_id = ? ORDER BY id",
            ("tenant_b",),
        )
        b_rows = cursor.fetchall()
        assert len(b_rows) == 1
        assert b_rows[0][0] == "GENESIS"

        # Hashes must be different (different content + different chains)
        assert h_a1 != h_b1

    def test_tenant_id_persisted(self, sync_db):
        """Tenant ID is correctly stored in the transaction row."""
        ledger = SovereignLedger(sync_db)
        ledger.record_transaction(
            "proj", "store", {"k": "v"}, tenant_id="my_tenant"
        )

        cursor = sync_db.execute(
            "SELECT tenant_id FROM transactions WHERE id = 1"
        )
        row = cursor.fetchone()
        assert row[0] == "my_tenant"


@pytest.mark.asyncio
class TestAsyncTenantScoping:
    """Test tenant isolation on the async path."""

    async def test_async_tenant_chain_isolation(self, async_db):
        """Async record_transaction_async scopes chains by tenant."""
        ledger = SovereignLedger(async_db)

        # Need to ensure schema exists
        await async_db.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project     TEXT NOT NULL,
                action      TEXT NOT NULL,
                detail      TEXT,
                prev_hash   TEXT NOT NULL,
                hash        TEXT NOT NULL UNIQUE,
                tenant_id   TEXT DEFAULT 'default',
                timestamp   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS merkle_roots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                root_hash       TEXT NOT NULL,
                tx_start_id     INTEGER NOT NULL,
                tx_end_id       INTEGER NOT NULL,
                tx_count        INTEGER NOT NULL,
                signature       TEXT,
                created_at      TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ','now')
                )
            );
            CREATE TABLE IF NOT EXISTS integrity_checks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                check_type      TEXT NOT NULL,
                status          TEXT NOT NULL,
                details         TEXT,
                started_at      TEXT NOT NULL,
                completed_at    TEXT NOT NULL
            );
        """)
        await async_db.commit()

        h_a = await ledger.record_transaction_async(
            "p", "store", {"x": 1}, tenant_id="alpha"
        )
        h_b = await ledger.record_transaction_async(
            "p", "store", {"x": 2}, tenant_id="beta"
        )
        h_a2 = await ledger.record_transaction_async(
            "p", "store", {"x": 3}, tenant_id="alpha"
        )

        # Alpha chain: GENESIS -> h_a -> h_a2
        cursor = await async_db.execute(
            "SELECT prev_hash FROM transactions "
            "WHERE tenant_id = ? ORDER BY id",
            ("alpha",),
        )
        rows = await cursor.fetchall()
        assert rows[0][0] == "GENESIS"
        assert rows[1][0] == h_a

        # Beta chain: GENESIS -> h_b (only 1 tx)
        cursor = await async_db.execute(
            "SELECT prev_hash FROM transactions "
            "WHERE tenant_id = ? ORDER BY id",
            ("beta",),
        )
        rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "GENESIS"

    async def test_audit_integrity_per_tenant(self, async_db):
        """audit_integrity_async scoped to a tenant validates only that chain."""
        ledger = SovereignLedger(async_db)

        # Setup schema
        await async_db.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project     TEXT NOT NULL,
                action      TEXT NOT NULL,
                detail      TEXT,
                prev_hash   TEXT NOT NULL,
                hash        TEXT NOT NULL UNIQUE,
                tenant_id   TEXT DEFAULT 'default',
                timestamp   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS merkle_roots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                root_hash       TEXT NOT NULL,
                tx_start_id     INTEGER NOT NULL,
                tx_end_id       INTEGER NOT NULL,
                tx_count        INTEGER NOT NULL,
                signature       TEXT,
                created_at      TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ','now')
                )
            );
            CREATE TABLE IF NOT EXISTS integrity_checks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                check_type      TEXT NOT NULL,
                status          TEXT NOT NULL,
                details         TEXT,
                started_at      TEXT NOT NULL,
                completed_at    TEXT NOT NULL
            );
        """)
        await async_db.commit()

        # Write 3 txs for tenant_a, 2 for tenant_b
        for i in range(3):
            await ledger.record_transaction_async(
                "p", "store", {"i": i}, tenant_id="t_a"
            )
        for i in range(2):
            await ledger.record_transaction_async(
                "p", "store", {"i": i}, tenant_id="t_b"
            )

        result_a = await ledger.audit_integrity_async(tenant_id="t_a")
        assert result_a["valid"] is True
        assert result_a["tx_count"] == 3
        assert result_a["tenant"] == "t_a"

        result_b = await ledger.audit_integrity_async(tenant_id="t_b")
        assert result_b["valid"] is True
        assert result_b["tx_count"] == 2
        assert result_b["tenant"] == "t_b"
