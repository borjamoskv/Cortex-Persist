#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""Tests for Ouroboros Thermodynamic Pruning Engine v2.0.

Covers:
    - _build_topological_barrier() recursive ancestor protection
    - execute_thermal_purge() dry-run, tier transitions, C5 immunity, JSON output
    - Edge cases: empty DB, all-C5, circular parents, missing DB
"""

import json
import os
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
import tempfile

import pytest

# Import the module under test
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from ouroboros_prune import (
    COLD_THRESHOLD,
    MIN_EXERGY_THRESHOLD,
    WARM_THRESHOLD,
    PurgeCycleStats,
    _build_topological_barrier,
    execute_thermal_purge,
)

# ─── Fixtures ────────────────────────────────────────────────────────

FACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    content TEXT,
    confidence TEXT DEFAULT 'C3',
    is_tombstoned INTEGER DEFAULT 0,
    parent_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    decay_half_life REAL DEFAULT 30.0,
    quadrant TEXT DEFAULT 'ACTIVE',
    storage_tier TEXT DEFAULT 'HOT',
    exergy_score REAL DEFAULT 1.0,
    updated_at TEXT,
    kinetic_mass REAL DEFAULT 1.0,
    last_accessed_at REAL,
    last_boosted_at REAL,
    access_count INTEGER DEFAULT 0
);
"""


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary SQLite DB with the facts schema."""
    db_path = str(tmp_path / "test_cortex.db")
    conn = sqlite3.connect(db_path)
    conn.execute(FACTS_SCHEMA)
    conn.commit()
    conn.close()
    return db_path


def _insert_fact(db_path: str, **kwargs) -> int:
    """Insert a fact and return its ID."""
    defaults = {
        "content": "test fact",
        "confidence": "C3",
        "is_tombstoned": 0,
        "parent_id": None,
        "created_at": "datetime('now')",
        "decay_half_life": 30.0,
        "quadrant": "ACTIVE",
        "storage_tier": "HOT",
        "exergy_score": 1.0,
    }
    defaults.update(kwargs)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Handle created_at: if it uses datetime(), use raw SQL
    created_at = defaults.pop("created_at")
    if created_at.startswith("datetime("):
        sql = (
            f"INSERT INTO facts (content, confidence, is_tombstoned, parent_id, "
            f"created_at, decay_half_life, quadrant, storage_tier, exergy_score) "
            f"VALUES (?, ?, ?, ?, {created_at}, ?, ?, ?, ?)"
        )
        cursor.execute(
            sql,
            (
                defaults["content"],
                defaults["confidence"],
                defaults["is_tombstoned"],
                defaults["parent_id"],
                defaults["decay_half_life"],
                defaults["quadrant"],
                defaults["storage_tier"],
                defaults["exergy_score"],
            ),
        )
    else:
        sql = (
            "INSERT INTO facts (content, confidence, is_tombstoned, parent_id, "
            "created_at, decay_half_life, quadrant, storage_tier, exergy_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        cursor.execute(
            sql,
            (
                defaults["content"],
                defaults["confidence"],
                defaults["is_tombstoned"],
                defaults["parent_id"],
                created_at,
                defaults["decay_half_life"],
                defaults["quadrant"],
                defaults["storage_tier"],
                defaults["exergy_score"],
            ),
        )

    fact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return fact_id


def _get_fact(db_path: str, fact_id: int) -> dict:
    """Read a fact by ID."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


# ═══════════════════════════════════════════════════════════════════════
# Tests: _build_topological_barrier
# ═══════════════════════════════════════════════════════════════════════


class TestBuildTopologicalBarrier:
    """Tests for recursive ancestor protection via C5 lineage."""

    def test_barrier_protects_direct_parent_of_c5(self, tmp_db):
        """A direct parent of a C5 fact must be in the barrier."""
        parent_id = _insert_fact(tmp_db, content="parent fact", confidence="C3")
        _insert_fact(tmp_db, content="c5 child", confidence="C5", parent_id=parent_id)

        conn = sqlite3.connect(tmp_db)
        barrier = _build_topological_barrier(conn)
        conn.close()

        assert parent_id in barrier

    def test_barrier_protects_grandparent_chain(self, tmp_db):
        """All ancestors in the chain up to a C5 fact must be protected."""
        grandparent_id = _insert_fact(tmp_db, content="grandparent")
        parent_id = _insert_fact(tmp_db, content="parent", parent_id=grandparent_id)
        _insert_fact(tmp_db, content="c5 leaf", confidence="C5", parent_id=parent_id)

        conn = sqlite3.connect(tmp_db)
        barrier = _build_topological_barrier(conn)
        conn.close()

        assert parent_id in barrier
        assert grandparent_id in barrier

    def test_barrier_empty_when_no_c5_facts(self, tmp_db):
        """No C5 facts → empty barrier set."""
        _insert_fact(tmp_db, content="c3 fact", confidence="C3")
        _insert_fact(tmp_db, content="c4 fact", confidence="C4")

        conn = sqlite3.connect(tmp_db)
        barrier = _build_topological_barrier(conn)
        conn.close()

        assert barrier == set()

    def test_barrier_empty_when_c5_has_no_parent(self, tmp_db):
        """C5 fact with parent_id=NULL → nothing to protect."""
        _insert_fact(tmp_db, content="c5 orphan", confidence="C5", parent_id=None)

        conn = sqlite3.connect(tmp_db)
        barrier = _build_topological_barrier(conn)
        conn.close()

        assert barrier == set()

    def test_barrier_ignores_tombstoned_c5(self, tmp_db):
        """Tombstoned C5 facts should not seed the barrier."""
        parent_id = _insert_fact(tmp_db, content="parent")
        _insert_fact(
            tmp_db,
            content="dead c5",
            confidence="C5",
            parent_id=parent_id,
            is_tombstoned=1,
        )

        conn = sqlite3.connect(tmp_db)
        barrier = _build_topological_barrier(conn)
        conn.close()

        assert parent_id not in barrier

    def test_barrier_handles_circular_parents(self, tmp_db):
        """Circular parent references must not cause infinite loop.

        BFS naturally terminates because visited nodes go into `protected`
        and are never re-added to the frontier.
        """
        # Create A → B → A cycle, with a C5 node pointing to A
        id_a = _insert_fact(tmp_db, content="fact A")
        id_b = _insert_fact(tmp_db, content="fact B", parent_id=id_a)
        # Update A's parent to B (creating cycle)
        conn = sqlite3.connect(tmp_db)
        conn.execute("UPDATE facts SET parent_id = ? WHERE id = ?", (id_b, id_a))
        conn.commit()
        # C5 fact pointing into the cycle
        _insert_fact(tmp_db, content="c5 node", confidence="C5", parent_id=id_a)

        barrier = _build_topological_barrier(conn)
        conn.close()

        # Both nodes in the cycle should be protected (no crash)
        assert id_a in barrier
        assert id_b in barrier

    def test_barrier_deep_chain(self, tmp_db):
        """Barrier traverses a 10-level ancestor chain."""
        ids = []
        parent = None
        for i in range(10):
            fid = _insert_fact(tmp_db, content=f"level-{i}", parent_id=parent)
            ids.append(fid)
            parent = fid
        # C5 at the leaf
        _insert_fact(tmp_db, content="c5 deep leaf", confidence="C5", parent_id=ids[-1])

        conn = sqlite3.connect(tmp_db)
        barrier = _build_topological_barrier(conn)
        conn.close()

        # All 10 ancestors should be protected
        for fid in ids:
            assert fid in barrier


# ═══════════════════════════════════════════════════════════════════════
# Tests: execute_thermal_purge
# ═══════════════════════════════════════════════════════════════════════


class TestExecuteThermalPurge:
    """Tests for the full Ouroboros thermodynamic pruning cycle."""

    def test_empty_database(self, tmp_db):
        """Empty facts table → zero stats, no errors."""
        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.total_scanned == 0
        assert stats.tombstoned == 0
        assert stats.transitioned_warm == 0
        assert stats.transitioned_cold == 0
        assert stats.protected_by_topology == 0
        assert stats.errors == []

    def test_db_not_found(self, tmp_path):
        """Non-existent DB path → error in stats."""
        bad_path = str(tmp_path / "nonexistent.db")
        stats = execute_thermal_purge(bad_path)

        assert len(stats.errors) == 1
        assert "not found" in stats.errors[0].lower()

    def test_c5_facts_never_scanned(self, tmp_db):
        """C5 facts are excluded from scanning regardless of age."""
        # Very old C5 fact (would be tombstoned if it were C3)
        _insert_fact(
            tmp_db,
            content="eternal c5",
            confidence="C5",
            created_at="datetime('now', '-365 days')",
            decay_half_life=30.0,
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.total_scanned == 0
        assert stats.tombstoned == 0

    def test_all_c5_facts(self, tmp_db):
        """Database with only C5 facts → nothing scanned."""
        for i in range(5):
            _insert_fact(tmp_db, content=f"c5-{i}", confidence="C5")

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.total_scanned == 0

    def test_dry_run_no_mutations(self, tmp_db):
        """Dry-run computes stats but does NOT mutate the database."""
        fact_id = _insert_fact(
            tmp_db,
            content="old fact",
            confidence="C3",
            created_at="datetime('now', '-100 days')",
            decay_half_life=30.0,
            storage_tier="HOT",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=True)

        # Stats should show tombstoning intent
        assert stats.total_scanned == 1
        assert stats.tombstoned == 1

        # But the DB should be unchanged
        fact = _get_fact(tmp_db, fact_id)
        assert fact["is_tombstoned"] == 0
        assert fact["storage_tier"] == "HOT"
        assert fact["exergy_score"] == 1.0  # Not updated in dry-run

    def test_tombstone_below_min_exergy(self, tmp_db):
        """Fact with exergy < 0.125 (3+ half-lives old) should be tombstoned."""
        # 100 days old, half_life=30 → exergy = 0.5^(100/30) ≈ 0.099
        fact_id = _insert_fact(
            tmp_db,
            content="dying fact",
            confidence="C3",
            created_at="datetime('now', '-100 days')",
            decay_half_life=30.0,
            storage_tier="HOT",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.tombstoned == 1

        fact = _get_fact(tmp_db, fact_id)
        assert fact["is_tombstoned"] == 1
        assert fact["quadrant"] == "VOID"
        assert fact["storage_tier"] == "VOID"

    def test_hot_to_warm_transition(self, tmp_db):
        """Fact with exergy between 0.25 and 0.50 in HOT tier → transition to WARM."""
        # 35 days old, half_life=30 → exergy = 0.5^(35/30) ≈ 0.44
        fact_id = _insert_fact(
            tmp_db,
            content="aging fact",
            confidence="C3",
            created_at="datetime('now', '-35 days')",
            decay_half_life=30.0,
            storage_tier="HOT",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.transitioned_warm == 1

        fact = _get_fact(tmp_db, fact_id)
        assert fact["storage_tier"] == "WARM"

    def test_warm_to_cold_transition(self, tmp_db):
        """Fact with exergy between 0.125 and 0.25, not in COLD → transition to COLD."""
        # 65 days old, half_life=30 → exergy = 0.5^(65/30) ≈ 0.23
        fact_id = _insert_fact(
            tmp_db,
            content="cold fact",
            confidence="C3",
            created_at="datetime('now', '-65 days')",
            decay_half_life=30.0,
            storage_tier="WARM",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.transitioned_cold == 1

        fact = _get_fact(tmp_db, fact_id)
        assert fact["storage_tier"] == "COLD"
        assert fact["quadrant"] == "ARCHIVE"

    def test_already_cold_not_transitioned_again(self, tmp_db):
        """Fact already in COLD tier with same exergy range → no re-transition."""
        # 65 days old, half_life=30, already COLD
        fact_id = _insert_fact(
            tmp_db,
            content="already cold",
            confidence="C3",
            created_at="datetime('now', '-65 days')",
            decay_half_life=30.0,
            storage_tier="COLD",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        # Should NOT re-transition (already COLD)
        assert stats.transitioned_cold == 0
        assert stats.transitioned_warm == 0

    def test_topological_protection_prevents_tombstone(self, tmp_db):
        """An old fact that's ancestor of a C5 node must not be tombstoned."""
        # Very old non-C5 fact (would normally be tombstoned)
        ancestor_id = _insert_fact(
            tmp_db,
            content="old ancestor",
            confidence="C3",
            created_at="datetime('now', '-200 days')",
            decay_half_life=30.0,
            storage_tier="HOT",
        )
        # C5 child protecting the ancestor
        _insert_fact(
            tmp_db,
            content="c5 protector",
            confidence="C5",
            parent_id=ancestor_id,
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.protected_by_topology == 1
        assert stats.tombstoned == 0

        fact = _get_fact(tmp_db, ancestor_id)
        assert fact["is_tombstoned"] == 0

    def test_json_output_mode(self, tmp_db, capsys):
        """JSON output mode emits valid JSON with correct structure."""
        _insert_fact(
            tmp_db,
            content="json test",
            confidence="C3",
            created_at="datetime('now', '-100 days')",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False, json_output=True)

        captured = capsys.readouterr()
        data = json.loads(captured.out)

        assert "total_scanned" in data
        assert "tombstoned" in data
        assert "transitioned_warm" in data
        assert "transitioned_cold" in data
        assert "protected_by_topology" in data
        assert "exergy_scores_updated" in data
        assert "errors" in data
        assert isinstance(data["errors"], list)

    def test_exergy_score_updated_after_purge(self, tmp_db):
        """After a real purge, exergy_score column reflects computed decay value."""
        # Fresh fact → exergy ≈ 1.0
        fresh_id = _insert_fact(
            tmp_db,
            content="fresh",
            confidence="C3",
            created_at="datetime('now')",
            decay_half_life=30.0,
            exergy_score=0.0,  # intentionally wrong
        )
        # Aged fact → exergy ≈ 0.44
        aged_id = _insert_fact(
            tmp_db,
            content="aged",
            confidence="C3",
            created_at="datetime('now', '-35 days')",
            decay_half_life=30.0,
            exergy_score=0.0,  # intentionally wrong
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.exergy_scores_updated == 2

        fresh = _get_fact(tmp_db, fresh_id)
        aged = _get_fact(tmp_db, aged_id)

        # Fresh fact should have exergy close to 1.0
        assert fresh["exergy_score"] > 0.9

        # Aged fact (35d, half_life=30) should have exergy ≈ 0.44
        assert 0.3 < aged["exergy_score"] < 0.6

    def test_mixed_tier_transitions(self, tmp_db):
        """Multiple facts at different decay stages transition correctly."""
        # HOT → WARM (35 days)
        warm_id = _insert_fact(
            tmp_db,
            content="warm candidate",
            confidence="C3",
            created_at="datetime('now', '-35 days')",
            decay_half_life=30.0,
            storage_tier="HOT",
        )
        # HOT → COLD (65 days, starting from HOT so it goes to WARM first)
        # Actually, the engine checks COLD threshold first (<0.25 and not COLD),
        # so HOT fact at 65 days goes directly to COLD
        cold_id = _insert_fact(
            tmp_db,
            content="cold candidate",
            confidence="C3",
            created_at="datetime('now', '-65 days')",
            decay_half_life=30.0,
            storage_tier="HOT",
        )
        # Tombstone (100 days)
        tomb_id = _insert_fact(
            tmp_db,
            content="tombstone candidate",
            confidence="C3",
            created_at="datetime('now', '-100 days')",
            decay_half_life=30.0,
            storage_tier="HOT",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.total_scanned == 3
        assert stats.tombstoned == 1
        # The 65-day fact goes to COLD (exergy ≈ 0.23 < COLD_THRESHOLD)
        assert stats.transitioned_cold == 1
        # The 35-day fact is NOT transitioned to WARM because cold check
        # comes first. Let's verify: exergy ≈ 0.44, which is < WARM_THRESHOLD
        # and >= COLD_THRESHOLD, so it hits the WARM branch
        assert stats.transitioned_warm == 1

    def test_zero_half_life_tombstones_immediately(self, tmp_db):
        """A fresh fact with half_life=0.0 is immediately tombstoned."""
        fact_id = _insert_fact(
            tmp_db,
            content="zero half life",
            confidence="C3",
            decay_half_life=0.0,
            storage_tier="HOT",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.tombstoned == 1
        fact = _get_fact(tmp_db, fact_id)
        assert fact["is_tombstoned"] == 1
        assert fact["storage_tier"] == "VOID"

    def test_null_half_life_defaults_to_30(self, tmp_db):
        """Fact with NULL decay_half_life defaults to 30.0."""
        conn = sqlite3.connect(tmp_db)
        conn.execute(
            "INSERT INTO facts (content, confidence, is_tombstoned, "
            "created_at, decay_half_life, storage_tier) "
            "VALUES ('null hl', 'C3', 0, datetime('now', '-35 days'), NULL, 'HOT')"
        )
        conn.commit()
        conn.close()

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        # 35 days / 30 hl → exergy ≈ 0.44 → WARM transition
        assert stats.transitioned_warm == 1


class TestPurgeCycleStats:
    """Tests for the PurgeCycleStats dataclass."""

    def test_to_dict_returns_all_fields(self):
        stats = PurgeCycleStats(
            total_scanned=10,
            tombstoned=3,
            transitioned_warm=2,
            transitioned_cold=1,
            protected_by_topology=4,
            exergy_scores_updated=10,
            distilled_facts=5,
            errors=["test error"],
        )
        d = stats.to_dict()

        assert d["total_scanned"] == 10
        assert d["tombstoned"] == 3
        assert d["transitioned_warm"] == 2
        assert d["transitioned_cold"] == 1
        assert d["protected_by_topology"] == 4
        assert d["exergy_scores_updated"] == 10
        assert d["distilled_facts"] == 5
        assert d["errors"] == ["test error"]

    def test_default_stats_all_zero(self):
        stats = PurgeCycleStats()
        d = stats.to_dict()

        assert all(v == 0 for k, v in d.items() if k != "errors")
        assert d["errors"] == []


class TestOuroborosDistillation:
    """Tests Phase 1.5: Kolmogorov Semantic Collapse & AST Distillation."""

    def test_python_code_distillation(self, tmp_db):
        """A decayed C3 Python fact is distilled to structural skeleton and saved as C5."""
        source_code = (
            "def calculate_exergy(node):\n"
            "    # Core logic\n"
            "    value = 42\n"
            "    return value\n"
        )
        fact_id = _insert_fact(
            tmp_db,
            content=source_code,
            confidence="C3",
            created_at="datetime('now', '-100 days')",
            decay_half_life=30.0,
            storage_tier="HOT",
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.tombstoned == 1
        assert stats.distilled_facts >= 1

        # Original fact should be tombstoned
        orig = _get_fact(tmp_db, fact_id)
        assert orig["is_tombstoned"] == 1

        # Check if there is a new C5 fact
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM facts WHERE confidence = 'C5' AND is_tombstoned = 0").fetchall()
        conn.close()

        assert len(rows) == 1
        new_fact = dict(rows[0])
        assert new_fact["confidence"] == "C5"
        assert "def calculate_exergy(node):" in new_fact["content"]
        assert "value = 42" not in new_fact["content"] # Body should be pruned!

    def test_text_semantic_fusion(self, tmp_db):
        """Two redundant text facts are fused into a single C5 primitive."""
        fact1_id = _insert_fact(
            tmp_db,
            content="This is the first fact containing sovereign proof logic",
            confidence="C3",
            created_at="datetime('now', '-100 days')",
            decay_half_life=30.0,
        )
        # Redundant content (high similarity)
        fact2_id = _insert_fact(
            tmp_db,
            content="This is the first fact containing sovereign proof logics",
            confidence="C4",
            created_at="datetime('now', '-100 days')",
            decay_half_life=30.0,
        )

        stats = execute_thermal_purge(tmp_db, dry_run=False)

        assert stats.tombstoned == 2
        # Fused group becomes 1 fact
        assert stats.distilled_facts >= 1

        # Check if there is a new C5 fact representing the fusion
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM facts WHERE confidence = 'C5' AND is_tombstoned = 0").fetchall()
        conn.close()

        assert len(rows) == 1
        new_fact = dict(rows[0])
        assert new_fact["confidence"] == "C5"
        assert "Fused Semantic Primitive" in new_fact["content"]
        assert str(fact1_id) in new_fact["content"]
        assert str(fact2_id) in new_fact["content"]
