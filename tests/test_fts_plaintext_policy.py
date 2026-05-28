"""Tests for Issue #95 — define the plaintext policy for FTS indexing.

Encryption happens at the storage layer. FTS may index plaintext for searchable
non-sensitive facts, but must not retain plaintext for privacy-flagged facts.
"""

import json
import sqlite3

import aiosqlite
import pytest

from cortex.crypto.aes import CortexEncrypter
from cortex.database.schema import CREATE_FACTS
from cortex.database.schema_extensions import CREATE_FACTS_FTS
from cortex.engine.fact_store_core import insert_fact_record
from cortex.migrations.mig_fts import _migration_017_fts_decouple
from cortex.search.hybrid import hybrid_search
from cortex.search.text import text_search

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


def _setup_sync_facts(conn: sqlite3.Connection) -> None:
    for stmt in CREATE_FACTS.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s + ";")
    conn.commit()


def _insert_sync_encrypted_fact(
    conn: sqlite3.Connection,
    encrypter: CortexEncrypter,
    *,
    tenant_id: str,
    content: str,
    metadata: dict,
) -> int:
    encrypted = encrypter.encrypt_str(content, tenant_id=tenant_id)
    cursor = conn.execute(
        "INSERT INTO facts "
        "(tenant_id, project, content, fact_type, confidence, valid_from, tags, "
        "source, metadata, exergy_score, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            tenant_id,
            "audit",
            encrypted,
            "knowledge",
            "C5",
            "2026-01-01",
            "[]",
            "migration-test",
            json.dumps(metadata),
            1.0,
            "2026-01-01",
            "2026-01-01",
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


@pytest.mark.asyncio
async def test_fts_indexes_plaintext_not_ciphertext(encrypter, monkeypatch):
    """Verify that FTS search works on encrypted facts because FTS stores plaintext."""
    # 1. Setup Mocking
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    # Stub hash and other components to avoid overhead
    monkeypatch.setattr("cortex.engine.fact_store_core.compute_fact_hash", lambda x: "hash")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    # 2. Ingest a non-sensitive encrypted fact
    secret_content = "The diamond is hidden in the blue vase"
    project = "heist"
    # insert_fact_record handles encryption internally via get_default_encrypter
    # and it SHOULD insert PLAINTEXT into facts_fts.
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
        meta={},
        tx_id=None,
    )
    # 3. Verify Storage Layer is Ciphertext
    async with conn.execute("SELECT content FROM facts WHERE id = ?", (fact_id,)) as cursor:
        row = await cursor.fetchone()
        stored_content = row[0]
        assert stored_content.startswith(encrypter.PREFIX)
        assert secret_content not in stored_content

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
async def test_privacy_flagged_fact_not_written_to_plaintext_fts(encrypter, monkeypatch):
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    monkeypatch.setattr("cortex.engine.fact_store_core.compute_fact_hash", lambda x: "hash")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    fact_id = await insert_fact_record(
        conn,
        tenant_id="tenant_a",
        project="audit",
        content="api_key = sk_dummy_1234567890123456789",
        fact_type="knowledge",
        tags=["security"],
        confidence="C5",
        ts=None,
        source="agent",
        meta={"privacy_flagged": True, "privacy_score": "0.9"},
        tx_id=None,
    )

    async with conn.execute("SELECT content FROM facts_fts WHERE rowid = ?", (fact_id,)) as cursor:
        row = await cursor.fetchone()

    assert row is None
    await conn.close()


@pytest.mark.asyncio
async def test_high_privacy_score_fact_not_written_to_plaintext_fts(encrypter, monkeypatch):
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    monkeypatch.setattr("cortex.engine.fact_store_core.compute_fact_hash", lambda x: "hash")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    fact_id = await insert_fact_record(
        conn,
        tenant_id="tenant_a",
        project="audit",
        content="private recovery phrase alpha beta gamma",
        fact_type="knowledge",
        tags=["security"],
        confidence="C5",
        ts=None,
        source="agent",
        meta={"privacy_score": 0.8},
        tx_id=None,
    )

    async with conn.execute("SELECT content FROM facts_fts WHERE rowid = ?", (fact_id,)) as cursor:
        row = await cursor.fetchone()

    assert row is None
    await conn.close()


@pytest.mark.asyncio
async def test_plaintext_fts_override_indexes_flagged_fact(encrypter, monkeypatch):
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    monkeypatch.setattr("cortex.engine.fact_store_core.compute_fact_hash", lambda x: "hash")
    monkeypatch.setenv("CORTEX_ALLOW_PLAINTEXT_FTS", "1")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    fact_id = await insert_fact_record(
        conn,
        tenant_id="tenant_a",
        project="audit",
        content="override searchable sensitive content",
        fact_type="knowledge",
        tags=["security"],
        confidence="C5",
        ts=None,
        source="agent",
        meta={"privacy_flagged": True, "privacy_score": 1.0},
        tx_id=None,
    )

    async with conn.execute("SELECT content FROM facts_fts WHERE rowid = ?", (fact_id,)) as cursor:
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "override searchable sensitive content"
    await conn.close()


@pytest.mark.asyncio
async def test_text_search_decrypts_with_authenticated_tenant(encrypter, monkeypatch):
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)
    monkeypatch.setattr("cortex.engine.fact_store_core.compute_fact_hash", lambda x: "hash")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    await insert_fact_record(
        conn,
        tenant_id="tenant_a",
        project="audit",
        content="tenant alpha secret memory",
        fact_type="knowledge",
        tags=["tenant"],
        confidence="C5",
        ts=None,
        source="agent",
        meta={},
        tx_id=None,
    )

    tenant_a_results = await text_search(
        conn,
        query="alpha",
        tenant_id="tenant_a",
        project="audit",
        limit=1,
    )
    tenant_b_results = await text_search(
        conn,
        query="alpha",
        tenant_id="tenant_b",
        project="audit",
        limit=1,
    )

    assert tenant_a_results
    assert tenant_a_results[0].content == "tenant alpha secret memory"
    assert not tenant_a_results[0].content.startswith(encrypter.PREFIX)
    assert tenant_b_results == []
    await conn.close()


def test_migration_017_recreates_facts_fts_with_tenant_column(encrypter, monkeypatch, tmp_path):
    monkeypatch.setattr("cortex.migrations.mig_fts.get_default_encrypter", lambda: encrypter)

    conn = sqlite3.connect(str(tmp_path / "migration.db"))
    try:
        _setup_sync_facts(conn)
        fact_id = _insert_sync_encrypted_fact(
            conn,
            encrypter,
            tenant_id="tenant_a",
            content="non sensitive migration content",
            metadata={},
        )

        _migration_017_fts_decouple(conn)

        columns = {row[1] for row in conn.execute("PRAGMA table_info(facts_fts)").fetchall()}
        row = conn.execute(
            "SELECT content, tenant_id FROM facts_fts WHERE rowid = ?",
            (fact_id,),
        ).fetchone()
    finally:
        conn.close()

    assert {"content", "project", "tags", "fact_type", "tenant_id"} <= columns
    assert row == ("non sensitive migration content", "tenant_a")


def test_migration_017_skips_privacy_flagged_plaintext(encrypter, monkeypatch, tmp_path):
    monkeypatch.setattr("cortex.migrations.mig_fts.get_default_encrypter", lambda: encrypter)

    conn = sqlite3.connect(str(tmp_path / "migration-private.db"))
    try:
        _setup_sync_facts(conn)
        fact_id = _insert_sync_encrypted_fact(
            conn,
            encrypter,
            tenant_id="tenant_a",
            content="api_key = sk_dummy_1234567890123456789",
            metadata={"privacy_flagged": True, "privacy_score": "0.9"},
        )

        _migration_017_fts_decouple(conn)

        row = conn.execute("SELECT content FROM facts_fts WHERE rowid = ?", (fact_id,)).fetchone()
    finally:
        conn.close()

    assert row is None
