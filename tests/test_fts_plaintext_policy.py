"""Tests for the explicit plaintext opt-in policy for FTS indexing.

Facts and metadata are encrypted at rest by default. FTS may duplicate plaintext
only when metadata explicitly opts into that tradeoff.
"""

import sqlite3

import aiosqlite
import pytest

from cortex.crypto.aes import CortexEncrypter
from cortex.database.schema import CREATE_FACTS
from cortex.database.schema_extensions import CREATE_FACTS_FTS
from cortex.engine.fact_store_core import insert_fact_record
from cortex.search.hybrid import hybrid_search

# Fixed key for testing
TEST_MASTER_KEY = b"1" * 32


@pytest.fixture
def encrypter():
    return CortexEncrypter(TEST_MASTER_KEY)


async def _setup_db(conn: aiosqlite.Connection) -> None:
    await conn.executescript("""
        CREATE TABLE causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER NOT NULL,
            parent_id INTEGER,
            signal_id INTEGER,
            edge_type TEXT NOT NULL DEFAULT 'triggered_by',
            project TEXT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE fact_tags (
            fact_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            PRIMARY KEY (fact_id, tag)
        );
        CREATE TABLE fact_embeddings (
            fact_id INTEGER PRIMARY KEY,
            embedding BLOB,
            k INTEGER,
            distance REAL
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    for stmt in CREATE_FACTS.strip().split(";"):
        s = stmt.strip()
        if s:
            await conn.execute(s + ";")
    await conn.executescript(CREATE_FACTS_FTS)
    await conn.commit()


@pytest.mark.asyncio
async def test_fts_indexes_plaintext_only_with_explicit_opt_in(encrypter, monkeypatch):
    """Verify that FTS search works only for facts that explicitly opt in."""
    # 1. Setup Mocking
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    # Stub hash and other components to avoid overhead
    monkeypatch.setattr("cortex.engine.fact_store_core.compute_fact_hash", lambda x: "hash")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    # 2. Ingest an encrypted fact with explicit plaintext-search opt-in.
    secret_content = "The diamond is hidden in the blue vase"
    project = "heist"
    fact_id = await insert_fact_record(
        conn,
        tenant_id="default",
        project=project,
        content=secret_content,
        fact_type="knowledge",
        tags=["security"],
        confidence="C5",
        ts=None,
        source="agent",
        meta={"allow_plaintext_fts": True, "classification": "public-search"},
        tx_id=None,
    )
    # 3. Verify Storage Layer is Ciphertext
    async with conn.execute(
        "SELECT content, metadata FROM facts WHERE id = ?", (fact_id,)
    ) as cursor:
        row = await cursor.fetchone()
        stored_content = row[0]
        stored_metadata = row[1]
        assert stored_content.startswith(encrypter.PREFIX)
        assert stored_metadata.startswith(encrypter.PREFIX)
        assert secret_content not in stored_content
        assert "public-search" not in stored_metadata

    # 4. Verify FTS Search works with plaintext keywords
    # This proves facts_fts has the decrypted content.
    results = await hybrid_search(
        conn,
        query="diamond vase",
        query_embedding=[0.0] * 384,  # Mock embedding (won't match vector search)
        project=project,
        vector_weight=0.0,  # Force only text search
        text_weight=1.0,
    )

    assert len(results) > 0
    assert results[0].fact_id == fact_id
    # content is decrypted by hybrid_search using get_default_encrypter
    assert results[0].content == secret_content
    await conn.close()


@pytest.mark.asyncio
async def test_fts_skips_default_facts_and_encrypts_metadata(encrypter, monkeypatch):
    """Default facts must not duplicate plaintext into FTS or plaintext metadata."""
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    monkeypatch.setattr("cortex.engine.fact_store_core.compute_fact_hash", lambda x: "hash")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    sensitive_content = "internal launch code delta seven"
    fact_id = await insert_fact_record(
        conn,
        tenant_id="default",
        project="heist",
        content=sensitive_content,
        fact_type="knowledge",
        tags=["security"],
        confidence="C5",
        ts=None,
        source="agent",
        meta={"classification": "internal-only"},
        tx_id=None,
    )

    async with conn.execute(
        "SELECT content, metadata FROM facts WHERE id = ?", (fact_id,)
    ) as cursor:
        row = await cursor.fetchone()
    assert row[0].startswith(encrypter.PREFIX)
    assert row[1].startswith(encrypter.PREFIX)
    assert sensitive_content not in row[0]
    assert "internal-only" not in row[1]

    async with conn.execute("SELECT COUNT(*) FROM facts_fts WHERE rowid = ?", (fact_id,)) as cursor:
        row = await cursor.fetchone()
    assert row[0] == 0

    await conn.close()


@pytest.mark.asyncio
async def test_fts_skips_privacy_flagged_facts(encrypter, monkeypatch):
    """Privacy-flagged facts must not duplicate plaintext into facts_fts."""
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    monkeypatch.setattr("cortex.engine.fact_store_core.compute_fact_hash", lambda x: "hash")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    secret_content = "API key sk-test_1234567890 should not enter FTS"
    fact_id = await insert_fact_record(
        conn,
        tenant_id="default",
        project="heist",
        content=secret_content,
        fact_type="knowledge",
        tags=["security"],
        confidence="C5",
        ts=None,
        source="agent",
        meta={"privacy_flagged": True, "privacy_matches": ["api_key"]},
        tx_id=None,
    )

    async with conn.execute("SELECT content FROM facts WHERE id = ?", (fact_id,)) as cursor:
        row = await cursor.fetchone()
    assert row[0].startswith(encrypter.PREFIX)
    assert secret_content not in row[0]

    async with conn.execute("SELECT COUNT(*) FROM facts_fts WHERE rowid = ?", (fact_id,)) as cursor:
        row = await cursor.fetchone()
    assert row[0] == 0

    results = await hybrid_search(
        conn,
        query="sk-test_1234567890",
        query_embedding=[0.0] * 384,
        project="heist",
        vector_weight=0.0,
        text_weight=1.0,
    )

    assert results == []
    await conn.close()


def test_fts_migration_skips_privacy_flagged_backfill(encrypter, monkeypatch) -> None:
    """Migration 017 must not backfill plaintext for sensitive facts."""
    from cortex.migrations.mig_fts import _migration_017_fts_decouple

    monkeypatch.setattr("cortex.migrations.mig_fts.get_default_encrypter", lambda: encrypter)

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE facts ("
        "id INTEGER PRIMARY KEY, content TEXT, project TEXT, tags TEXT, fact_type TEXT, "
        "tenant_id TEXT, valid_until TEXT, metadata TEXT)"
    )
    conn.execute("CREATE VIRTUAL TABLE facts_fts USING fts5(content)")
    conn.execute(
        "INSERT INTO facts "
        "(id, content, project, tags, fact_type, tenant_id, valid_until, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, NULL, ?)",
        (
            1,
            encrypter.encrypt_str("public searchable memory", tenant_id="default"),
            "p",
            "[]",
            "knowledge",
            "default",
            '{"allow_plaintext_fts": true}',
        ),
    )
    conn.execute(
        "INSERT INTO facts "
        "(id, content, project, tags, fact_type, tenant_id, valid_until, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, NULL, ?)",
        (
            2,
            encrypter.encrypt_str("secret memory should stay out", tenant_id="default"),
            "p",
            "[]",
            "knowledge",
            "default",
            '{"privacy_flagged": true}',
        ),
    )
    conn.commit()

    _migration_017_fts_decouple(conn)

    public_rows = conn.execute(
        "SELECT rowid FROM facts_fts WHERE content MATCH 'searchable'"
    ).fetchall()
    secret_rows = conn.execute("SELECT rowid FROM facts_fts WHERE content MATCH 'secret'").fetchall()

    assert public_rows == [(1,)]
    assert secret_rows == []
    conn.close()
