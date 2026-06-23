# [C5-REAL] Exergy-Maximized
import pytest
import aiosqlite
import json
from babylon60.engine.causality import (
    CausalGraph,
    LedgerEvent,
    ValidationStatus,
    propagate_refutation,
    AsyncCausalGraph,
    TaintStatus,
    Confidence,
    _downgrade_confidence,
    KRGSE_DERIVED_FROM,
    KRGSE_TAINTED_BY,
)


def test_confidence_downgrade():
    """Validates confidence level downgrading."""
    assert _downgrade_confidence("C5", 1) == "C4"
    assert _downgrade_confidence("C5", 4) == "C1"
    assert _downgrade_confidence("C5", 10) == "C1"
    assert _downgrade_confidence("C1", 1) == "C1"
    assert _downgrade_confidence("INVALID", 1) == "C1"


def test_causal_graph_sync():
    """Validates synchronous CausalGraph operations."""
    graph = CausalGraph()
    e1 = LedgerEvent("e1", [], ValidationStatus.TEST_PASSED, 1.0, "2023-01-01")
    e2 = LedgerEvent("e2", ["e1"], ValidationStatus.CONJECTURE, 0.8, "2023-01-02")

    graph.add_event(e1)
    graph.add_event(e2)

    assert graph.get_event("e1") == e1
    assert graph.get_descendants("e1") == ["e2"]
    assert graph["e2"] == e2


def test_propagate_refutation():
    """Validates refutation propagation and trust score decay."""
    graph = CausalGraph()
    e1 = LedgerEvent("e1", [], ValidationStatus.TEST_PASSED, 1.0, "t1")
    e2 = LedgerEvent("e2", ["e1"], ValidationStatus.CONJECTURE, 1.0, "t2")
    e3 = LedgerEvent("e3", ["e2"], ValidationStatus.CONJECTURE, 1.0, "t3")

    graph.add_event(e1)
    graph.add_event(e2)
    graph.add_event(e3)

    propagate_refutation(graph, "e1", decay=0.5)

    assert graph["e1"].status == ValidationStatus.REFUTED
    assert graph["e1"].trust_score == 0.0

    assert graph["e2"].tainted is True
    assert graph["e2"].trust_score < 1.0

    assert graph["e3"].tainted is True
    # Penalty decreases with depth in current implementation:
    # e2 (depth 1): trust = 1.0 * (1 - 0.5/1) = 0.5
    # e3 (depth 2): trust = 1.0 * (1 - 0.5/2) = 0.75
    assert graph["e3"].trust_score > graph["e2"].trust_score


@pytest.mark.asyncio
async def test_async_causal_graph_ops(tmp_path):
    """Validates AsyncCausalGraph database operations and blast radius."""
    db_path = tmp_path / "test_causality.db"
    async with aiosqlite.connect(db_path) as conn:
        # We need facts table for foreign keys
        await conn.execute(
            "CREATE TABLE facts (id INTEGER PRIMARY KEY, confidence TEXT, tenant_id TEXT, metadata TEXT)"
        )

        acg = AsyncCausalGraph(conn)
        await acg.ensure_table()

        # Insert some facts
        await conn.execute("INSERT INTO facts (id, confidence, tenant_id) VALUES (1, 'C5', 't1')")
        await conn.execute("INSERT INTO facts (id, confidence, tenant_id) VALUES (2, 'C5', 't1')")
        await conn.execute("INSERT INTO facts (id, confidence, tenant_id) VALUES (3, 'C5', 't1')")

        # Record edges: 1 -> 2 -> 3
        await acg.record_edge(fact_id=2, parent_id=1, tenant_id="t1")
        await acg.record_edge(fact_id=3, parent_id=2, tenant_id="t1")

        radius = await acg.calculate_blast_radius(1, "t1")
        assert radius == 2  # 2 and 3 are descendants

        radius_empty = await acg.calculate_blast_radius(3, "t1")
        assert radius_empty == 0


@pytest.mark.asyncio
async def test_propagate_taint_async(tmp_path):
    """Validates asynchronous taint propagation through the causal graph."""
    db_path = tmp_path / "test_taint.db"
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "CREATE TABLE facts (id INTEGER PRIMARY KEY, confidence TEXT, tenant_id TEXT, metadata TEXT)"
        )

        acg = AsyncCausalGraph(conn)
        await acg.ensure_table()

        # Setup: 1 (source) -> 2 -> 3
        await conn.execute(
            "INSERT INTO facts (id, confidence, tenant_id, metadata) VALUES (1, 'C5', 'default', '{}')"
        )
        await conn.execute(
            "INSERT INTO facts (id, confidence, tenant_id, metadata) VALUES (2, 'C5', 'default', '{}')"
        )
        await conn.execute(
            "INSERT INTO facts (id, confidence, tenant_id, metadata) VALUES (3, 'C5', 'default', '{}')"
        )

        await acg.record_edge(fact_id=2, parent_id=1)
        await acg.record_edge(fact_id=3, parent_id=2)

        report = await acg.propagate_taint(fact_id=1)

        assert report.source_fact_id == 1
        assert report.affected_count == 3  # 1, 2, and 3

        # Verify changes in DB
        async with conn.execute("SELECT id, confidence, metadata FROM facts ORDER BY id") as cursor:
            rows = await cursor.fetchall()

            # Fact 1: Tainted, C1 (floor_to_c1=True by default)
            assert rows[0][1] == "C1"
            meta1 = json.loads(rows[0][2])
            assert meta1["taint_status"] == TaintStatus.TAINTED.value

            # Fact 2: Suspect (derived from tainted), C1
            assert rows[1][1] == "C1"
            meta2 = json.loads(rows[1][2])
            assert meta2["taint_status"] == TaintStatus.TAINTED.value
            # Actually _derive_node_status:
            # if all(s == TaintStatus.TAINTED for s in p_states): return TaintStatus.TAINTED

            # Verify audit edges
            async with conn.execute(
                "SELECT COUNT(*) FROM causal_edges WHERE edge_type = ?", (KRGSE_TAINTED_BY,)
            ) as cursor:
                row = await cursor.fetchone()
                assert row[0] == 2  # Taint edges from 1 to 2 and 1 to 3
