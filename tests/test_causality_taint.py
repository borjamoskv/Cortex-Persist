"""Tests for taint propagation in causality engine — Ω₁₃ §15.9."""

from __future__ import annotations

import json
import sqlite3

import pytest

from cortex.engine.causality import (
    CONFIDENCE_LEVELS,
    EDGE_DERIVED_FROM,
    TaintReport,
    _downgrade_confidence,
)

# ── Unit Tests: Confidence Downgrade ──────────────────────────────────


class TestDowngradeConfidence:
    def test_single_hop(self) -> None:
        assert _downgrade_confidence("C5", 1) == "C4"
        assert _downgrade_confidence("C4", 1) == "C3"
        assert _downgrade_confidence("C3", 1) == "C2"
        assert _downgrade_confidence("C2", 1) == "C1"

    def test_floor_at_c1(self) -> None:
        assert _downgrade_confidence("C1", 1) == "C1"
        assert _downgrade_confidence("C1", 5) == "C1"

    def test_multi_hop(self) -> None:
        assert _downgrade_confidence("C5", 2) == "C3"
        assert _downgrade_confidence("C5", 4) == "C1"
        assert _downgrade_confidence("C5", 10) == "C1"

    def test_unknown_confidence(self) -> None:
        assert _downgrade_confidence("X9", 1) == "C1"
        assert _downgrade_confidence("", 1) == "C1"

    def test_zero_hops(self) -> None:
        assert _downgrade_confidence("C5", 0) == "C5"


# ── Integration Tests: Taint Propagation ──────────────────────────────


def _create_db(conn: sqlite3.Connection) -> None:
    """Create minimal schema for taint tests."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            fact_type TEXT DEFAULT 'decision',
            confidence TEXT DEFAULT 'C5',
            metadata TEXT DEFAULT '{}',
            valid_from TEXT DEFAULT '',
            valid_until TEXT DEFAULT NULL,
            tenant_id TEXT DEFAULT 'default',
            project TEXT DEFAULT 'test'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER,
            parent_id INTEGER,
            signal_id INTEGER,
            edge_type TEXT DEFAULT 'derived_from',
            project TEXT DEFAULT 'test',
            tenant_id TEXT DEFAULT 'default',
            created_at TEXT DEFAULT ''
        )
    """)
    conn.commit()


def _insert_fact(conn: sqlite3.Connection, fact_id: int, confidence: str = "C5") -> None:
    conn.execute(
        "INSERT INTO facts (id, content, confidence) VALUES (?, ?, ?)",
        (fact_id, f"fact-{fact_id}", confidence),
    )
    conn.commit()


def _insert_edge(
    conn: sqlite3.Connection, fact_id: int, parent_id: int, edge_type: str = EDGE_DERIVED_FROM
) -> None:
    conn.execute(
        "INSERT INTO causal_edges (fact_id, parent_id, edge_type, tenant_id) VALUES (?, ?, ?, ?)",
        (fact_id, parent_id, edge_type, "default"),
    )
    conn.commit()


@pytest.mark.asyncio
async def test_propagate_taint_single_child() -> None:
    """One descendant gets confidence downgraded."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA journal_mode=WAL")

    from cortex.engine.causality import AsyncCausalGraph

    graph = AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        "CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT, confidence TEXT, metadata TEXT DEFAULT '{}', valid_until TEXT)"
    )

    # Create facts: 1 → 2 (parent → child)
    await conn.execute(
        "INSERT INTO facts (id, content, confidence) VALUES (?, ?, ?)",
        (1, "parent-fact", "C5"),
    )
    await conn.execute(
        "INSERT INTO facts (id, content, confidence) VALUES (?, ?, ?)",
        (2, "child-fact", "C5"),
    )
    await conn.execute(
        "INSERT INTO causal_edges (fact_id, parent_id, edge_type, tenant_id) VALUES (?, ?, ?, ?)",
        (2, 1, EDGE_DERIVED_FROM, "default"),
    )
    await conn.commit()

    # Invalidate fact 1 → taint propagates to fact 2
    report = await graph.propagate_taint(1)

    assert isinstance(report, TaintReport)
    assert report.source_fact_id == 1
    # Source (fact 1) drops to C1, child (fact 2) gets downgraded.
    assert report.affected_count >= 1

    changes_by_id = {c["fact_id"]: c for c in report.confidence_changes}
    if 2 in changes_by_id:
        change = changes_by_id[2]
        assert change["old_confidence"] == "C5"
        # Child is downgraded by at least 1 step.
        assert change["new_confidence"] in ("C1", "C2", "C3", "C4")
        assert "status" in change

    # Verify DB updated — Ω₁₃ cascade: child inherits parent's C1 floor.
    async with conn.execute("SELECT confidence, metadata FROM facts WHERE id = 2") as cursor:
        row = await cursor.fetchone()
    assert row[0] == "C1"
    meta = json.loads(row[1])
    assert meta["tainted_by"] == 1
    assert "taint_timestamp" in meta

    await conn.close()


@pytest.mark.asyncio
async def test_propagate_taint_chain() -> None:
    """3-deep chain: each hop increases degradation."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    graph_mod = __import__("cortex.engine.causality", fromlist=["AsyncCausalGraph"])
    graph = graph_mod.AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        "CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT, confidence TEXT, metadata TEXT DEFAULT '{}', valid_until TEXT)"
    )

    # Chain: 1 → 2 → 3 → 4
    for fid in range(1, 5):
        await conn.execute(
            "INSERT INTO facts (id, content, confidence) VALUES (?, ?, ?)",
            (fid, f"fact-{fid}", "C5"),
        )
    for parent, child in [(1, 2), (2, 3), (3, 4)]:
        await conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, edge_type, tenant_id) "
            "VALUES (?, ?, ?, ?)",
            (child, parent, EDGE_DERIVED_FROM, "default"),
        )
    await conn.commit()

    report = await graph.propagate_taint(1)

    # Source (fact 1) drops to C1; children get cascading degradation.
    assert report.affected_count >= 3
    changes_by_id = {c["fact_id"]: c for c in report.confidence_changes}
    # Each child must be downgraded from its original C5.
    for fid in (2, 3, 4):
        assert changes_by_id[fid]["old_confidence"] == "C5"
        assert changes_by_id[fid]["new_confidence"] != "C5"

    await conn.close()


@pytest.mark.asyncio
async def test_propagate_taint_no_descendants() -> None:
    """No descendants → empty report."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    graph_mod = __import__("cortex.engine.causality", fromlist=["AsyncCausalGraph"])
    graph = graph_mod.AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        "CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT, confidence TEXT, metadata TEXT DEFAULT '{}', valid_until TEXT)"
    )

    await conn.execute(
        "INSERT INTO facts (id, content, confidence) VALUES (?, ?, ?)",
        (1, "lone-fact", "C5"),
    )
    await conn.commit()

    report = await graph.propagate_taint(1)
    # Source node itself gets downgraded C5→C1 (counted in affected_count).
    # No descendants means no additional propagation.
    assert report.affected_count == 1
    assert len(report.confidence_changes) == 1
    assert report.confidence_changes[0]["fact_id"] == 1

    await conn.close()


@pytest.mark.asyncio
async def test_propagate_taint_cyclic_graph() -> None:
    """Cyclic dependencies should not cause infinite loops and terminate correctly."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    graph_mod = __import__("cortex.engine.causality", fromlist=["AsyncCausalGraph"])
    graph = graph_mod.AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        "CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT, confidence TEXT, metadata TEXT DEFAULT '{}', valid_until TEXT)"
    )

    # Chain: 1 → 2 → 3 → 1 (Cycle)
    for fid in range(1, 4):
        await conn.execute(
            "INSERT INTO facts (id, content, confidence) VALUES (?, ?, ?)",
            (fid, f"fact-{fid}", "C5"),
        )
    for parent, child in [(1, 2), (2, 3), (3, 1)]:
        await conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, edge_type, tenant_id) "
            "VALUES (?, ?, ?, ?)",
            (child, parent, EDGE_DERIVED_FROM, "default"),
        )
    await conn.commit()

    report = await graph.propagate_taint(1)

    # Terminated cleanly despite the cycle.
    assert report.affected_count >= 2

    await conn.close()


@pytest.mark.asyncio
async def test_taint_report_structure() -> None:
    """TaintReport has correct frozen fields."""
    report = TaintReport(
        source_fact_id=42,
        affected_count=3,
        confidence_changes=[
            {"fact_id": 1, "old_confidence": "C5", "new_confidence": "C4", "hops": 1},
        ],
    )
    assert report.source_fact_id == 42
    assert report.affected_count == 3
    assert len(report.confidence_changes) == 1

    # Frozen dataclass
    with pytest.raises(AttributeError):
        report.source_fact_id = 99  # type: ignore[misc]


class TestConfidenceLevels:
    def test_ordered(self) -> None:
        assert CONFIDENCE_LEVELS == ["C5", "C4", "C3", "C2", "C1"]
