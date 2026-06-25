# [C5-REAL] Exergy-Maximized
"""Tests for Issue #95 - define a single plaintext policy for FTS indexing.

FTS should always index the plaintext content, NOT the ciphertext.
Encryption should happen at the storage layer, but FTS (which is plaintext search)
should only contain decrypted data to enable searchability (or be disabled for sensitive data).
CORTEX policy: FTS indexes the PLAINTEXT provided at ingestion.
"""

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------
import pytest

from babylon60.crypto.aes import CortexEncrypter
from babylon60.database.schema import CREATE_FACTS
from babylon60.database.schema_extensions import CREATE_FACTS_FTS
from babylon60.engine.fact_store_core import insert_fact_record
from babylon60.search.hybrid import hybrid_search

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
async def test_fts_indexes_plaintext_not_ciphertext(encrypter, monkeypatch):
    """Verify that FTS search works on encrypted facts because FTS stores plaintext."""
    # 1. Setup Mocking
    monkeypatch.setattr("babylon60.crypto.get_default_encrypter", lambda: encrypter)
    # Stub hash and other components to avoid overhead
    monkeypatch.setattr("babylon60.engine.fact_store_core.compute_fact_hash", lambda x: "hash")

    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    # 2. Ingest an encrypted fact
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
