"""Tests for taint propagation in causality engine — Ω₁₃ §15.9."""

from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock

import pytest

from cortex.crypto import get_default_encrypter
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
        """CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            action TEXT,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT,
            timestamp TEXT,
            tenant_id TEXT DEFAULT 'default'
        )"""
    )
    await conn.execute(
        """CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            confidence TEXT,
            metadata TEXT DEFAULT '{}',
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            valid_until TEXT
        )"""
    )

    # Use encrypter for metadata — Ω₁₃ §15.9.
    enc = get_default_encrypter()
    encrypted_meta = enc.encrypt_json({}, tenant_id="default")

    # Create facts: 1 → 2 (parent → child)
    await conn.execute(
        "INSERT INTO facts (id, content, confidence, metadata) VALUES (?, ?, ?, ?)",
        (1, "parent-fact", "C5", encrypted_meta),
    )
    await conn.execute(
        "INSERT INTO facts (id, content, confidence, metadata) VALUES (?, ?, ?, ?)",
        (2, "child-fact", "C5", encrypted_meta),
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
    assert report.affected_count == 1
    assert len(report.confidence_changes) == 1

    change = report.confidence_changes[0]
    assert change["fact_id"] == 2
    assert change["old_confidence"] == "C5"
    assert change["new_confidence"] == "C4"
    assert change["hops"] == 1

    # Verify DB updated
    async with conn.execute("SELECT confidence, metadata FROM facts WHERE id = 2") as cursor:
        row = await cursor.fetchone()
    assert row[0] == "C4"
    metadata = enc.decrypt_json(row[1], tenant_id="default")
    assert metadata["tainted_by"] == 1
    assert "taint_timestamp" in metadata

    await conn.close()


@pytest.mark.asyncio
async def test_propagate_taint_records_ledger_transaction() -> None:
    """Taint propagation must persist its audit event into the ledger."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    from cortex.engine.causality import AsyncCausalGraph

    graph = AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        """CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            action TEXT,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT,
            timestamp TEXT,
            tenant_id TEXT DEFAULT 'default'
        )"""
    )
    await conn.execute(
        """CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            confidence TEXT,
            metadata TEXT DEFAULT '{}',
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            valid_until TEXT
        )"""
    )

    enc = get_default_encrypter()
    encrypted_meta = enc.encrypt_json({}, tenant_id="default")

    await conn.execute(
        "INSERT INTO facts (id, content, confidence, metadata, project) VALUES (?, ?, ?, ?, ?)",
        (1, "parent-fact", "C5", encrypted_meta, "ledger-test"),
    )
    await conn.execute(
        "INSERT INTO facts (id, content, confidence, metadata, project) VALUES (?, ?, ?, ?, ?)",
        (2, "child-fact", "C5", encrypted_meta, "ledger-test"),
    )
    await conn.execute(
        "INSERT INTO causal_edges (fact_id, parent_id, edge_type, tenant_id, project) "
        "VALUES (?, ?, ?, ?, ?)",
        (2, 1, EDGE_DERIVED_FROM, "default", "ledger-test"),
    )
    await conn.commit()

    report = await graph.propagate_taint(1)

    assert report.affected_count == 1
    async with conn.execute(
        "SELECT project, action, detail, tenant_id FROM transactions ORDER BY id DESC LIMIT 1"
    ) as cursor:
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "ledger-test"
    assert row[1] == "propagate_taint"
    assert '"source_fact_id": 1' in row[2]
    assert row[3] == "default"

    await conn.close()


@pytest.mark.asyncio
async def test_propagate_taint_chain() -> None:
    """3-deep chain: each hop increases degradation."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    from cortex.engine.causality import AsyncCausalGraph

    graph = AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        """CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            action TEXT,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT,
            timestamp TEXT,
            tenant_id TEXT DEFAULT 'default'
        )"""
    )
    await conn.execute(
        """CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            confidence TEXT,
            metadata TEXT DEFAULT '{}',
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            valid_until TEXT
        )"""
    )

    # Use encrypter for metadata — Ω₁₃ §15.9.
    enc = get_default_encrypter()
    encrypted_meta = enc.encrypt_json({}, tenant_id="default")

    # Chain: 1 → 2 → 3 → 4
    for fid in range(1, 5):
        await conn.execute(
            "INSERT INTO facts (id, content, confidence, metadata) VALUES (?, ?, ?, ?)",
            (fid, f"fact-{fid}", "C5", encrypted_meta),
        )
    for parent, child in [(1, 2), (2, 3), (3, 4)]:
        await conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, edge_type, tenant_id) "
            "VALUES (?, ?, ?, ?)",
            (child, parent, EDGE_DERIVED_FROM, "default"),
        )
    await conn.commit()

    report = await graph.propagate_taint(1)

    assert report.affected_count == 3
    # Fact 2: 1 hop → C4, Fact 3: 2 hops → C3, Fact 4: 3 hops → C2
    changes_by_id = {c["fact_id"]: c for c in report.confidence_changes}
    assert changes_by_id[2]["new_confidence"] == "C4"
    assert changes_by_id[3]["new_confidence"] == "C3"
    assert changes_by_id[4]["new_confidence"] == "C2"

    await conn.close()


@pytest.mark.asyncio
async def test_propagate_taint_no_descendants() -> None:
    """No descendants → empty report."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    from cortex.engine.causality import AsyncCausalGraph

    graph = AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        """CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            action TEXT,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT,
            timestamp TEXT,
            tenant_id TEXT DEFAULT 'default'
        )"""
    )
    await conn.execute(
        """CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            confidence TEXT,
            metadata TEXT DEFAULT '{}',
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            valid_until TEXT
        )"""
    )

    await conn.execute(
        "INSERT INTO facts (id, content, confidence) VALUES (?, ?, ?)",
        (1, "lone-fact", "C5"),
    )
    await conn.commit()

    report = await graph.propagate_taint(1)
    assert report.affected_count == 0
    assert report.confidence_changes == []

    await conn.close()


@pytest.mark.asyncio
async def test_propagate_taint_cyclic_graph() -> None:
    """Cyclic dependencies should not cause infinite loops and terminate correctly."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    from cortex.engine.causality import AsyncCausalGraph

    graph = AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        """CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            action TEXT,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT,
            timestamp TEXT,
            tenant_id TEXT DEFAULT 'default'
        )"""
    )
    await conn.execute(
        """CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            confidence TEXT,
            metadata TEXT DEFAULT '{}',
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            valid_until TEXT
        )"""
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
    assert report.affected_count == 2
    assert {change["fact_id"] for change in report.confidence_changes} == {2, 3}

    await conn.close()


@pytest.mark.asyncio
async def test_calculate_blast_radius_cyclic_graph() -> None:
    """Blast radius calculation must terminate and exclude the source node in a cycle."""
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    from cortex.engine.causality import AsyncCausalGraph

    graph = AsyncCausalGraph(conn)
    await graph.ensure_table()
    await conn.execute(
        """CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            confidence TEXT,
            metadata TEXT DEFAULT '{}',
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            valid_until TEXT
        )"""
    )

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

    radius = await graph.calculate_blast_radius(1, tenant_id="default")

    assert radius == 2

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


@pytest.mark.asyncio
async def test_episodic_sealer_awaits_ledger_write() -> None:
    """Anamnesis sealing must await the ledger write before returning."""
    from cortex.engine.causality import EpisodicSealer

    ledger = AsyncMock()
    sealer = EpisodicSealer(ledger=ledger)

    await sealer.seal_context(
        agent_key="agent.alpha",
        data={"fact_count": 3},
        metadata={"project": "CORTEX_SYSTEM", "tenant_id": "tenant_a", "sequence": 7},
    )

    ledger.record_transaction.assert_awaited_once()
    kwargs = ledger.record_transaction.await_args.kwargs
    assert kwargs["project"] == "CORTEX_SYSTEM"
    assert kwargs["action"] == "anamnesis_seal"
    assert kwargs["tenant_id"] == "tenant_a"
    assert kwargs["detail"]["agent_key"] == "agent.alpha"


class TestConfidenceLevels:
    def test_ordered(self) -> None:
        assert CONFIDENCE_LEVELS == ["C5", "C4", "C3", "C2", "C1"]
