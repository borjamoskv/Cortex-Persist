# [C5-REAL] Exergy-Maximized
import json
import sqlite3
import pytest
import aiosqlite

from babylon60.search.text import text_search
from babylon60.search.vector import _build_semantic_query


@pytest.mark.asyncio
async def test_text_search_dynamic_filtering():
    """
    Verifies that text_search correctly filters results using dynamic
    criteria such as fact_type and tags in SQLite.
    """
    async with aiosqlite.connect(":memory:") as conn:
        # Create facts table structure
        await conn.execute("""
            CREATE TABLE facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                project     TEXT NOT NULL,
                content     TEXT NOT NULL,
                fact_type   TEXT NOT NULL DEFAULT 'knowledge',
                tags        TEXT DEFAULT '[]',
                valid_from  TEXT,
                valid_until TEXT,
                confidence  TEXT DEFAULT 'C3',
                confidence_rank INTEGER DEFAULT 3,
                consensus_score REAL DEFAULT 1.0,
                is_tombstoned INTEGER NOT NULL DEFAULT 0,
                hash        TEXT,
                tx_id       INTEGER,
                source      TEXT,
                metadata    TEXT DEFAULT '{}',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Insert test facts
        await conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags) VALUES (?, ?, ?, ?)",
            (
                "p1",
                "cortex semantic search with dynamic filtering",
                "knowledge",
                json.dumps(["cortex", "filtering"]),
            ),
        )
        await conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags) VALUES (?, ?, ?, ?)",
            (
                "p1",
                "exergy storage and cortex memory limits decision",
                "decision",
                json.dumps(["exergy", "cortex"]),
            ),
        )
        await conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags) VALUES (?, ?, ?, ?)",
            ("p1", "some unrelated information fact", "knowledge", json.dumps(["unrelated"])),
        )
        await conn.commit()

        # Test case 1: Query content "cortex" with no filters (should match facts 1 and 2)
        results = await text_search(conn, "cortex", tenant_id="default", project="p1")
        assert len(results) == 2

        # Test case 2: Query content "cortex" with fact_type="knowledge" (should match fact 1 only)
        results = await text_search(
            conn, "cortex", tenant_id="default", project="p1", fact_type="knowledge"
        )
        assert len(results) == 1
        assert "dynamic filtering" in results[0].content

        # Test case 3: Query content "cortex" with tags=["exergy"] (should match fact 2 only)
        results = await text_search(
            conn, "cortex", tenant_id="default", project="p1", tags=["exergy"]
        )
        assert len(results) == 1
        assert "exergy storage" in results[0].content

        # Test case 4: Query content "cortex" with tag "filtering" and fact_type="decision" (should match none)
        results = await text_search(
            conn,
            "cortex",
            tenant_id="default",
            project="p1",
            tags=["filtering"],
            fact_type="decision",
        )
        assert len(results) == 0


def test_build_semantic_query_dynamic_filtering():
    """
    Verifies that _build_semantic_query correctly appends the SQL filters
    for fact_type and tags and appends their variables to params.
    """
    tenant_id = "test_tenant"
    embedding_json = "[1.0, 2.0]"
    top_k = 5
    project = "test_proj"
    as_of = None
    confidence = None

    # Base query without dynamic filters
    sql, params = _build_semantic_query(
        tenant_id, embedding_json, top_k, project, as_of, confidence
    )
    assert "AND f.fact_type = ?" not in sql
    assert "EXISTS (SELECT 1 FROM json_each(f.tags) WHERE value = ?)" not in sql

    # With fact_type and tags filters
    sql, params = _build_semantic_query(
        tenant_id,
        embedding_json,
        top_k,
        project,
        as_of,
        confidence,
        fact_type="decision",
        tags=["exergy", "cortex"],
    )

    assert "AND f.fact_type = ?" in sql
    assert "EXISTS (SELECT 1 FROM json_each(f.tags) WHERE value = ?)" in sql

    # Verify parameter order
    # Base params: [tenant_id, embedding_json, top_k*3, project] -> length 4
    # Plus fact_type, plus tag1, plus tag2 -> total length 7
    assert len(params) == 7
    assert params[4] == "decision"
    assert params[5] == "exergy"
    assert params[6] == "cortex"
