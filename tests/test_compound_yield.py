"""Tests for the CHRONOS-1 Compound Yield System (Axiom Ω₁₁)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from cortex.engine.compound_yield import (
    CompoundProjector,
    CompoundYieldTracker,
)

# ─── Projection Model Tests ──────────────────────────────────────────


def test_compound_projector_1_year():
    """1 year projection should equal linear."""
    res = CompoundProjector.project(base_hours_per_year=100.0, reuse_rate=0.15, years=1)
    assert res.total_linear == 100.0
    assert res.total_compound == 100.0
    assert res.multiplier == 1.0


def test_compound_projector_multi_year():
    """Multi-year projection should compound."""
    # 2 years at 100h / yr, r=0.15
    # Year 1: 100h
    # Year 2: 100h (this year) + 100 * 1.15 (last year compounding) = 215
    # Total = 315
    res = CompoundProjector.project(base_hours_per_year=100.0, reuse_rate=0.15, years=2)
    assert res.total_linear == 200.0
    assert res.total_compound == 315.0
    assert res.multiplier == 1.57


def test_compound_projector_10_year_exponential():
    """A decade projection should show massive exponential gain."""
    res = CompoundProjector.project(base_hours_per_year=5000.0, reuse_rate=0.15, years=10)
    assert res.total_linear == 50_000.0
    assert res.total_compound > 100_000.0
    assert res.multiplier > 2.0


# ─── Tracker Engine Tests ────────────────────────────────────────────


@pytest.fixture
def memory_db(tmp_path: Path):
    """Create a temporary SQLite DB mapped to CORTEX schema."""
    db_path = tmp_path / "test_compound.db"
    conn = sqlite3.connect(str(db_path))

    # Create required tables
    conn.executescript(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            project TEXT,
            content TEXT,
            fact_type TEXT,
            tags TEXT,
            confidence TEXT,
            valid_from TEXT,
            valid_until TEXT,
            source TEXT,
            metadata TEXT,
            consensus_score REAL,
            created_at TEXT,
            updated_at TEXT,
            tx_id INTEGER,
            hash TEXT
        );
        CREATE TABLE causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER,
            parent_id INTEGER,
            signal_id INTEGER,
            edge_type TEXT,
            project TEXT,
            tenant_id TEXT,
            created_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


def _insert_fact(db_path: str, fact_id: int, project: str, hours: float | None = 0.5):
    metadata = json.dumps({"hours_saved": hours}) if hours is not None else "{}"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO facts (id, project, metadata) VALUES (?, ?, ?)",
        (fact_id, project, metadata),
    )
    conn.commit()
    conn.close()


def _insert_edge(db_path: str, child_id: int, parent_id: int, project: str):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO causal_edges (fact_id, parent_id, project, edge_type) VALUES (?, ?, ?, 'derived_from')",
        (child_id, parent_id, project),
    )
    conn.commit()
    conn.close()


def test_tracker_empty_db(memory_db):
    tracker = CompoundYieldTracker(db_path=memory_db)
    report = tracker.analyze_chains()
    assert len(report.chains) == 0
    assert report.total_linear == 0.0
    assert report.total_compound == 0.0


def test_tracker_single_chain(memory_db):
    # Chain: 1 -> 2 -> 3
    # Hours: 1.0 each
    _insert_fact(memory_db, 1, "test", hours=1.0)
    _insert_fact(memory_db, 2, "test", hours=1.0)
    _insert_fact(memory_db, 3, "test", hours=1.0)

    _insert_edge(memory_db, 2, 1, "test")
    _insert_edge(memory_db, 3, 2, "test")

    tracker = CompoundYieldTracker(db_path=memory_db, reuse_rate=0.5)
    report = tracker.analyze_chains("test")

    assert len(report.chains) == 1
    chain = report.chains[0]
    assert chain.root_fact_id == 1
    assert chain.depth == 2
    assert len(chain.fact_ids) == 3

    # Calculation:
    # Node 1 (depth 0): 1.0 * 1.5^0 = 1.0
    # Node 2 (depth 1): 1.0 * 1.5^1 = 1.5
    # Node 3 (depth 2): 1.0 * 1.5^2 = 2.25
    # Total = 4.75
    assert chain.linear_hours == 3.0
    assert chain.compound_hours == 4.75
    assert report.total_linear == 3.0
    assert report.total_compound == 4.75
    assert round(report.multiplier, 2) == 1.58


def test_tracker_multiple_chains_and_isolated_nodes(memory_db):
    # Chain A: 10 -> 11 (Depth 1)
    _insert_fact(memory_db, 10, "sys", hours=2.0)
    _insert_fact(memory_db, 11, "sys", hours=2.0)
    _insert_edge(memory_db, 11, 10, "sys")

    # Chain B: 20 -> 21 -> 22 (Depth 2)
    _insert_fact(memory_db, 20, "sys", hours=100.0)
    _insert_fact(memory_db, 21, "sys", hours=10.0)
    _insert_fact(memory_db, 22, "sys", hours=10.0)
    _insert_edge(memory_db, 21, 20, "sys")
    _insert_edge(memory_db, 22, 21, "sys")

    # Isolated edge (doesn't connect to root cleanly, e.g. parent is null in reality,
    # but here let's just create an isolated fact with no parent and no child)
    _insert_fact(memory_db, 99, "sys", hours=50.0)

    tracker = CompoundYieldTracker(db_path=memory_db, reuse_rate=0.15)
    report = tracker.analyze_chains("sys")

    assert len(report.chains) == 2
    # Chain B should be first because it has higher compound hours (starts at 100)
    assert report.chains[0].root_fact_id == 20
    assert report.chains[1].root_fact_id == 10

    assert report.chains[0].depth == 2
    assert report.chains[1].depth == 1


def test_tracker_cycle_protection(memory_db):
    # Chain: 1 -> 2 -> 3 -> 1 (Cycle)
    _insert_fact(memory_db, 1, "cycle", hours=1.0)
    _insert_fact(memory_db, 2, "cycle", hours=1.0)
    _insert_fact(memory_db, 3, "cycle", hours=1.0)

    _insert_edge(memory_db, 2, 1, "cycle")
    _insert_edge(memory_db, 3, 2, "cycle")
    _insert_edge(memory_db, 1, 3, "cycle")  # The cycle!

    tracker = CompoundYieldTracker(db_path=memory_db, reuse_rate=0.15)
    # The analyze_chains method protects against infinite loops by keeping a visited_in_chain set.
    # We just need to make sure it doesn't hang.
    report = tracker.analyze_chains("cycle")

    # The BFS will pick one as an internal root (depending on set iteration order)
    # and traverse until it hits the cycle.
    # Actually, in a pure cycle, `has_parent` set will contain ALL nodes.
    # Therefore `roots = all_nodes - has_parent` will be empty.
    # So there are no roots.
    assert len(report.chains) == 0
