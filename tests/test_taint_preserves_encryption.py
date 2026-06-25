
# [C5-REAL] Exergy-Maximized
"""Tests for Issue #96 - preserve encrypted metadata during taint propagation.

Causality taint propagation must not corrupt encrypted metadata columns
or leak tenant-specific ciphertext across boundaries.
"""

import json

import aiosqlite

import pytest

from cortex.crypto.aes import CortexEncrypter
from cortex.engine.causality import KRGSE_DERIVED_FROM, AsyncCausalGraph, TaintStatus



# Use a fixed 32-byte master key for deterministic testing
TEST_MASTER_KEY = b"0" * 32


@pytest.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    # Setup schema matching Issue #96 requirements (facts with metadata/meta and tenant_id)
    await conn.executescript("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence TEXT DEFAULT 'C5',
            metadata TEXT DEFAULT '{}',
            is_tombstoned INTEGER DEFAULT 0
        );
        CREATE TABLE causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER NOT NULL,
            parent_id INTEGER,
            signal_id INTEGER,
            project TEXT DEFAULT 'general',
            edge_type TEXT NOT NULL DEFAULT 'triggered_by',
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (fact_id) REFERENCES facts(id)
        );
    """)
    yield conn
    await conn.close()


@pytest.fixture
def encrypter():
    return CortexEncrypter(TEST_MASTER_KEY)


@pytest.mark.asyncio
async def test_taint_preserves_encrypted_metadata(db, encrypter, monkeypatch):
    """Verify that propagating taint on encrypted metadata preserves it correctly."""

    # Mock the global encrypter used by AsyncCausalGraph
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    monkeypatch.setattr("cortex.engine.causality.get_default_encrypter", lambda: encrypter)

    graph = AsyncCausalGraph(db)
    tenant = "tenant-alpha"

    # 1. Create a parent and a child
    # Parent (ID 1)
    # Child (ID 2), derived from Parent

    secret_meta = {"secret_key": "vault-123", "original_status": "clean"}
    encrypted_meta_parent = encrypter.encrypt_json(secret_meta, tenant_id=tenant)
    encrypted_meta_child = encrypter.encrypt_json({"child_secret": "data-456"}, tenant_id=tenant)

    await db.execute(
        "INSERT INTO facts (id, tenant_id, project, content, confidence, metadata) VALUES (?, ?, ?, ?, ?, ?)",
        (1, tenant, "proj-1", "parent fact", "C5", encrypted_meta_parent),
    )
    await db.execute(
        "INSERT INTO facts (id, tenant_id, project, content, confidence, metadata) VALUES (?, ?, ?, ?, ?, ?)",
        (2, tenant, "proj-1", "child fact", "C5", encrypted_meta_child),
    )
    await db.execute(
        "INSERT INTO causal_edges (fact_id, parent_id, edge_type, tenant_id) VALUES (?, ?, ?, ?)",
        (2, 1, KRGSE_DERIVED_FROM, tenant),
    )
    await db.commit()

    # 2. Propagate Taint from Parent
    # THIS SHOULD FAIL OR CORRUPT if the bug exists (treating ciphertext as JSON)
    report = await graph.propagate_taint(1, tenant_id=tenant)

    assert report.affected_count >= 2  # Parent + Child

    # 3. Verify Integrity
    async with db.execute("SELECT id, metadata FROM facts ORDER BY id") as cursor:
        rows = await cursor.fetchall()

    for fid, meta_ciphertext in rows:
        # Decrypt and check
        try:
            decrypted = encrypter.decrypt_json(meta_ciphertext, tenant_id=tenant)
            assert decrypted is not None
            assert "taint_status" in decrypted
            assert decrypted["taint_status"] in (TaintStatus.TAINTED, TaintStatus.SUSPECT)

            if fid == 1:
                assert decrypted["secret_key"] == "vault-123"
            if fid == 2:
                assert decrypted["child_secret"] == "data-456"

        except Exception as e:
            pytest.fail(f"Metadata for fact {fid} was corrupted or failed decryption: {e}")


@pytest.mark.asyncio
async def test_taint_isolation_between_tenants(db, encrypter, monkeypatch):
    """Verify that taint does NOT cross tenant boundaries even if IDs overlap."""
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    monkeypatch.setattr("cortex.engine.causality.get_default_encrypter", lambda: encrypter)

    graph = AsyncCausalGraph(db)

    # Tenant Alpha: 1 -> 2
    # Tenant Beta: 3 -> 4

    await db.execute(
        "INSERT INTO facts (id, tenant_id, project, content) VALUES (1, 'alpha', 'p', 'a1')"
    )
    await db.execute(
        "INSERT INTO facts (id, tenant_id, project, content) VALUES (2, 'alpha', 'p', 'a2')"
    )
    await db.execute(
        "INSERT INTO causal_edges (fact_id, parent_id, tenant_id) VALUES (2, 1, 'alpha')"
    )

    await db.execute(
        "INSERT INTO facts (id, tenant_id, project, content) VALUES (3, 'beta', 'p', 'b1')"
    )
    await db.execute(
        "INSERT INTO facts (id, tenant_id, project, content) VALUES (4, 'beta', 'p', 'b2')"
    )
    await db.execute(
        "INSERT INTO causal_edges (fact_id, parent_id, tenant_id) VALUES (4, 3, 'beta')"
    )
    await db.commit()

    # Taint Alpha-1
    await graph.propagate_taint(1, tenant_id="alpha")

    # Check Beta-3 status (should be clean/untouched)
    async with db.execute("SELECT metadata FROM facts WHERE id = 3") as cursor:
        row = await cursor.fetchone()
        assert (
            row[0] == "{}" or row[0] is None or json.loads(row[0]).get("taint_status") != "tainted"
        )
