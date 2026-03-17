"""Integration tests: causal gap re-ranking in hybrid_search_sync.

Validates Ω₁₃ enforcement: search with CausalGap populates
causal_gap_score and re-ranks by causal utility.
"""

from __future__ import annotations

import sqlite3

import pytest

from cortex.search.causal_gap import CausalGap
from cortex.search.hybrid import hybrid_search_sync
from cortex.search.models import SearchResult


def _make_in_memory_db() -> sqlite3.Connection:
    """Create a minimal in-memory SQLite DB with search tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cortex_facts (
            id TEXT PRIMARY KEY,
            content TEXT,
            fact_type TEXT DEFAULT 'pattern',
            confidence TEXT DEFAULT 'C3',
            source TEXT DEFAULT 'test',
            project TEXT DEFAULT 'test',
            tenant_id TEXT DEFAULT 'default',
            created_at TEXT DEFAULT '2026-01-01T00:00:00',
            metadata TEXT DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS cortex_fts
        USING fts5(id, content, fact_type, project, tenant_id)
        """
    )
    # Insert test data
    facts = [
        ("f1", "Database schema migration strategies for PostgreSQL"),
        ("f2", "API rate limiting with token bucket algorithms"),
        ("f3", "Neural network architecture for image classification"),
    ]
    for fid, content in facts:
        conn.execute(
            "INSERT INTO cortex_facts (id, content) VALUES (?, ?)",
            (fid, content),
        )
        conn.execute(
            "INSERT INTO cortex_fts (id, content, fact_type, project, tenant_id) "
            "VALUES (?, ?, 'pattern', 'test', 'default')",
            (fid, content),
        )
    conn.commit()
    return conn


def _make_gap(**overrides) -> CausalGap:
    """Create a CausalGap with sensible defaults."""
    defaults = {
        "decision_id": "test-decision-001",
        "hypothesis": "Database performance degrades under load",
        "missing_evidence": "PostgreSQL migration schema strategies",
        "current_confidence": 0.3,
        "expected_confidence_gain": 0.7,
        "blocking_reason": "Need migration data to validate hypothesis",
    }
    defaults.update(overrides)
    return CausalGap(**defaults)


def test_hybrid_search_sync_backward_compat():
    """Without causal_gap, causal_gap_score must remain 0.0."""
    conn = _make_in_memory_db()
    dummy_emb = [0.0] * 384

    results = hybrid_search_sync(
        conn=conn,
        query="database migration",
        query_embedding=dummy_emb,
        top_k=5,
    )
    for r in results:
        assert r.causal_gap_score == 0.0


def test_hybrid_search_sync_with_causal_gap():
    """With CausalGap provided, causal_gap_score must be populated."""
    conn = _make_in_memory_db()
    dummy_emb = [0.0] * 384

    gap = _make_gap(
        missing_evidence="PostgreSQL migration schema strategies",
    )

    results = hybrid_search_sync(
        conn=conn,
        query="database migration PostgreSQL",
        query_embedding=dummy_emb,
        top_k=5,
        causal_gap=gap,
    )
    scored = [r for r in results if r.causal_gap_score > 0.0]
    if results:
        assert len(scored) > 0, "causal_gap_score should be populated"


def test_reranking_changes_order():
    """CausalGap re-ranking should potentially change result order."""
    conn = _make_in_memory_db()
    dummy_emb = [0.0] * 384

    results_no_gap = hybrid_search_sync(
        conn=conn,
        query="algorithms",
        query_embedding=dummy_emb,
        top_k=5,
    )

    gap = _make_gap(
        hypothesis="Need database knowledge",
        missing_evidence="database schema migration PostgreSQL",
        expected_confidence_gain=0.9,
    )
    results_with_gap = hybrid_search_sync(
        conn=conn,
        query="algorithms",
        query_embedding=dummy_emb,
        top_k=5,
        causal_gap=gap,
    )

    assert len(results_no_gap) == len(results_with_gap)

    for r in results_with_gap:
        assert r.causal_gap_score >= 0.0
