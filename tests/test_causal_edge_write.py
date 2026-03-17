"""Tests for causal edge creation in the write path.

Verifies that insert_fact_record creates causal_edges when
parent_decision_id is resolved (Ω₁₁ densification fix).
"""

from __future__ import annotations

import json

import aiosqlite
import pytest

from cortex.engine.fact_store_core import insert_fact_record

# ── Helpers ─────────────────────────────────────────────────────────────


async def _setup_db(conn: aiosqlite.Connection) -> None:
    """Create minimal schema for causal edge tests."""
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT DEFAULT 'default',
            project TEXT,
            content TEXT,
            fact_type TEXT,
            tags TEXT,
            confidence TEXT DEFAULT 'stated',
            valid_from TEXT,
            valid_until TEXT,
            source TEXT,
            meta TEXT,
            hash TEXT,
            signature TEXT,
            signer_pubkey TEXT,
            is_quarantined INTEGER DEFAULT 0,
            quarantined_at TEXT,
            quarantine_reason TEXT,
            is_tombstoned INTEGER DEFAULT 0,
            parent_decision_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            consensus_score REAL DEFAULT 1.0,
            tx_id INTEGER,
            expires_at TEXT,
            last_accessed_at TEXT,
            tombstoned_at TEXT,
            cognitive_layer TEXT,
            haiku TEXT,
            falsification_test TEXT
        );
        CREATE TABLE IF NOT EXISTS causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER NOT NULL,
            parent_id INTEGER,
            signal_id INTEGER,
            edge_type TEXT NOT NULL DEFAULT 'triggered_by',
            project TEXT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (fact_id) REFERENCES facts(id)
        );
        CREATE TABLE IF NOT EXISTS facts_fts (
            rowid INTEGER,
            content TEXT,
            project TEXT,
            tags TEXT,
            fact_type TEXT
        );
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            entity_type TEXT,
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            first_seen TEXT,
            last_seen TEXT,
            mention_count INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS entity_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id INTEGER,
            target_entity_id INTEGER,
            relation_type TEXT,
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            first_seen TEXT,
            last_seen TEXT,
            mention_count INTEGER DEFAULT 1
        );
    """)
    await conn.commit()


# ── Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_parent_decision_id_creates_causal_edge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fact with explicit parent_decision_id creates a derived_from edge."""
    # Stub crypto to avoid keyring/encryption
    monkeypatch.setattr(
        "cortex.engine.fact_store_core.compute_fact_hash",
        lambda x: "deadbeef",
    )

    class FakeEnc:
        def encrypt_str(self, s: str, **kw: object) -> str:
            return s

        def encrypt_json(self, d: object, **kw: object) -> str:
            return json.dumps(d)

    monkeypatch.setattr(
        "cortex.crypto.get_default_encrypter", lambda: FakeEnc()
    )

    class FakeSigner:
        can_sign = False

    monkeypatch.setattr(
        "cortex.extensions.security.signatures.get_default_signer",
        lambda: FakeSigner(),
    )

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    # Create the parent fact first
    await conn.execute(
        "INSERT INTO facts (id, project, content, fact_type, "
        "tenant_id, is_tombstoned) "
        "VALUES (100, 'test', 'parent', 'decision', 'default', 0)"
    )
    await conn.commit()

    # Insert a new fact with parent_decision_id=100
    fact_id = await insert_fact_record(
        conn,
        tenant_id="default",
        project="test",
        content="child decision",
        fact_type="decision",
        tags=["test"],
        confidence="stated",
        ts=None,
        source=None,
        meta={},
        tx_id=None,
        parent_decision_id=100,
    )

    # Verify causal edge was created
    async with conn.execute(
        "SELECT fact_id, parent_id, edge_type FROM causal_edges"
    ) as cursor:
        edges = await cursor.fetchall()

    assert len(edges) >= 1
    edge = edges[0]
    assert edge[0] == fact_id
    assert edge[1] == 100
    assert edge[2] == "derived_from"

    await conn.close()


@pytest.mark.asyncio
async def test_auto_resolved_parent_creates_edge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto-resolved parent_decision_id (for decisions) creates edge."""
    monkeypatch.setattr(
        "cortex.engine.fact_store_core.compute_fact_hash",
        lambda x: "deadbeef",
    )

    class FakeEnc:
        def encrypt_str(self, s: str, **kw: object) -> str:
            return s

        def encrypt_json(self, d: object, **kw: object) -> str:
            return json.dumps(d)

    monkeypatch.setattr(
        "cortex.crypto.get_default_encrypter", lambda: FakeEnc()
    )

    class FakeSigner:
        can_sign = False

    monkeypatch.setattr(
        "cortex.extensions.security.signatures.get_default_signer",
        lambda: FakeSigner(),
    )

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    # Create a prior decision in the same project
    await conn.execute(
        "INSERT INTO facts (id, project, content, fact_type, "
        "tenant_id, is_tombstoned) "
        "VALUES (50, 'myproject', 'prior decision', 'decision', "
        "'default', 0)"
    )
    await conn.commit()

    # Insert a new decision WITHOUT explicit parent — should auto-resolve
    fact_id = await insert_fact_record(
        conn,
        tenant_id="default",
        project="myproject",
        content="new decision",
        fact_type="decision",
        tags=[],
        confidence="stated",
        ts=None,
        source=None,
        meta={},
        tx_id=None,
        # No parent_decision_id — should auto-resolve to 50
    )

    async with conn.execute(
        "SELECT fact_id, parent_id, edge_type FROM causal_edges"
    ) as cursor:
        edges = await cursor.fetchall()

    # Should have auto-created a derived_from edge to fact 50
    assert len(edges) >= 1
    # The newest fact should link back to 50
    matching = [e for e in edges if e[0] == fact_id and e[1] == 50]
    assert len(matching) == 1
    assert matching[0][2] == "derived_from"

    await conn.close()


@pytest.mark.asyncio
async def test_no_duplicate_edge_when_causal_parent_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When meta has causal_parent, parent_decision_id doesn't double-write."""
    monkeypatch.setattr(
        "cortex.engine.fact_store_core.compute_fact_hash",
        lambda x: "deadbeef",
    )

    class FakeEnc:
        def encrypt_str(self, s: str, **kw: object) -> str:
            return s

        def encrypt_json(self, d: object, **kw: object) -> str:
            return json.dumps(d)

    monkeypatch.setattr(
        "cortex.crypto.get_default_encrypter", lambda: FakeEnc()
    )

    class FakeSigner:
        can_sign = False

    monkeypatch.setattr(
        "cortex.extensions.security.signatures.get_default_signer",
        lambda: FakeSigner(),
    )

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    # Parent fact
    await conn.execute(
        "INSERT INTO facts (id, project, content, fact_type, "
        "tenant_id, is_tombstoned) "
        "VALUES (200, 'test', 'parent', 'decision', 'default', 0)"
    )
    await conn.commit()

    # Insert with BOTH causal_parent in meta AND parent_decision_id
    fact_id = await insert_fact_record(
        conn,
        tenant_id="default",
        project="test",
        content="child with both",
        fact_type="decision",
        tags=[],
        confidence="stated",
        ts=None,
        source=None,
        meta={"causal_parent": 999},  # signal-based edge
        tx_id=None,
        parent_decision_id=200,
    )

    async with conn.execute(
        "SELECT fact_id, parent_id, signal_id, edge_type "
        "FROM causal_edges"
    ) as cursor:
        edges = await cursor.fetchall()

    # Should have exactly 1 edge (from causal_parent), not 2
    fact_edges = [e for e in edges if e[0] == fact_id]
    assert len(fact_edges) == 1
    assert fact_edges[0][2] == 999  # signal_id
    assert fact_edges[0][3] == "triggered_by"

    await conn.close()
