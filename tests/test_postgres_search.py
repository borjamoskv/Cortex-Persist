# [C5-REAL] Exergy-Maximized
"""Tests for PostgreSQL & pgvector search paths (text, semantic, and hybrid)."""

from __future__ import annotations

import datetime
from typing import Any
import pytest

from cortex.search.models import SearchResult
from cortex.search.text import text_search
from cortex.search.vector import semantic_search
from cortex.search.hybrid import hybrid_search
from cortex.storage import StorageMode


class MockPostgresConn:
    def __init__(self, fetch_results: list[tuple] | None = None):
        self.fetch_results = fetch_results or []
        self.queries: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, sql: str, *args) -> list[tuple]:
        self.queries.append((sql, args))
        return self.fetch_results


@pytest.fixture
def mock_postgres_mode(monkeypatch):
    monkeypatch.setenv("CORTEX_STORAGE", "postgres")
    monkeypatch.setattr("cortex.storage.get_storage_mode", lambda: StorageMode.POSTGRES)
    monkeypatch.setattr("cortex.search.vector.get_storage_mode", lambda: StorageMode.POSTGRES)
    monkeypatch.setattr("cortex.search.text.get_storage_mode", lambda: StorageMode.POSTGRES)


@pytest.mark.asyncio
async def test_postgres_text_search(mock_postgres_mode):
    # Setup mock row returning:
    # 0: id, 1: content, 2: project, 3: fact_type, 4: confidence,
    # 5: valid_from, 6: valid_until, 7: tags, 8: source, 9: metadata,
    # 10: created_at, 11: updated_at, 12: tx_id, 13: hash,
    # 14: consensus_score, 15: confidence_rank
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_row = (
        "fact-1",
        "Plaintext fact content",
        "project-a",
        "knowledge",
        "C5",
        "2026-06-06T00:00:00Z",
        None,
        ["tag1", "tag2"],  # postgres returning tags as list directly
        "agent",  # source (index 8)
        {"meta_key": "meta_val"},  # postgres returning metadata as dict directly (index 9)
        now,  # created_at as datetime
        now,  # updated_at as datetime
        42,  # tx_id
        "tx-hash-xyz",
        1.5,  # consensus_score
        1.0,  # confidence_rank
    )

    conn = MockPostgresConn([mock_row])

    results = await text_search(
        conn=conn,
        query="cortex",
        tenant_id="tenant-123",
        project="project-a",
        fact_type="knowledge",
        tags=["tag1"],
        limit=10,
        confidence="C5",
    )

    assert len(results) == 1
    res = results[0]
    assert res.fact_id == "fact-1"
    assert res.tags == ["tag1", "tag2"]
    assert res.meta == {"meta_key": "meta_val", "consensus_score": 1.5}
    assert res.created_at == now
    assert res.tx_id == 42
    assert res.hash == "tx-hash-xyz"

    # Assert query structure is Postgres-compatible ($1, $2 and ILIKE)
    sql, args = conn.queries[0]
    assert "$1" in sql
    assert "ILIKE" in sql
    assert args[0] == "tenant-123"
    assert args[1] == "%cortex%"


@pytest.mark.asyncio
async def test_postgres_semantic_search(mock_postgres_mode):
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_row = (
        "fact-2",
        "Vector content",
        "project-b",
        "fact",
        "C4",
        "2026-06-06T00:00:00Z",
        None,
        ["vector-tag"],
        "agent",  # source (index 8)
        {"source": "llm"},  # metadata (index 9)
        0.15,  # distance (index 10)
        now,  # created_at
        now,  # updated_at
        99,  # tx_id
        "tx-hash-abc",
    )

    conn = MockPostgresConn([mock_row])

    results = await semantic_search(
        conn=conn,
        query_embedding=[0.1] * 384,
        top_k=5,
        tenant_id="tenant-456",
        project="project-b",
        confidence="C4",
    )

    assert len(results) == 1
    res = results[0]
    assert res.fact_id == "fact-2"
    assert res.score == 0.85  # 1.0 - 0.15 distance
    assert res.tags == ["vector-tag"]
    assert res.meta == {"source": "llm"}
    assert res.tx_id == 99

    sql, args = conn.queries[0]
    assert "$1" in sql
    assert "<=>" in sql
    assert args[0] == [0.1] * 384
    assert args[1] == "tenant-456"


@pytest.mark.asyncio
async def test_postgres_hybrid_search(mock_postgres_mode):
    # Mocking both text and semantic searches inside hybrid_search
    now = datetime.datetime.now(datetime.timezone.utc)
    text_row = (
        "fact-1",
        "Common content",
        "project-h",
        "fact",
        "C5",
        "2026-06-06T00:00:00Z",
        None,
        ["hybrid"],
        "agent",  # source
        {"foo": "bar"},  # metadata
        now,
        now,
        1,
        "hash-1",
        1.5,
        1.0,
    )

    vector_row = (
        "fact-1",
        "Common content",
        "project-h",
        "fact",
        "C5",
        "2026-06-06T00:00:00Z",
        None,
        ["hybrid"],
        "agent",  # source
        {"foo": "bar"},  # metadata
        0.1,  # distance
        now,
        now,
        1,
        "hash-1",
    )

    class SmartMockPostgresConn:
        def __init__(self):
            self.queries = []

        async def fetch(self, sql: str, *args) -> list[tuple]:
            self.queries.append((sql, args))
            if "ILIKE" in sql:
                return [text_row]
            elif "<=>" in sql:
                return [vector_row]
            return []

    conn = SmartMockPostgresConn()
    results = await hybrid_search(
        conn=conn,
        query="Common",
        query_embedding=[0.1] * 384,
        tenant_id="tenant-h",
        project="project-h",
        limit=5,
    )

    assert len(results) == 1
    assert results[0].fact_id == "fact-1"
    assert isinstance(results[0].created_at, datetime.datetime)
