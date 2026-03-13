"""Tests for Crystal Consolidation (REM Phase).

Tests the thermometer (temperature, resonance, quadrant classification)
and consolidator (cold purge, semantic merge, diamond promotion).
"""

from __future__ import annotations

import json
import sqlite3
import time

import numpy as np
import pytest

from cortex.swarm.crystal_consolidator import (
    ConsolidationResult,
    _execute_cold_purge,
    _execute_diamond_promotion,
    consolidate,
)
from cortex.swarm.crystal_thermometer import (
    TEMPERATURE_COLD,
    TEMPERATURE_HOT,
    CrystalVitals,
    calculate_resonance,
    calculate_temperature,
    classify_quadrant,
    determine_recommendation,
    measure_crystal_sync,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite DB with facts_meta and vec_facts tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE facts_meta (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            content TEXT,
            timestamp REAL,
            is_diamond INTEGER DEFAULT 0,
            is_bridge INTEGER DEFAULT 0,
            confidence TEXT DEFAULT 'C4',
            success_rate REAL DEFAULT 1.0,
            cognitive_layer TEXT DEFAULT 'semantic',
            parent_decision_id TEXT,
            metadata TEXT DEFAULT '{}'
        )
    """)
    # Use a plain table instead of vec0 (sqlite_vec not available in test)
    conn.execute("""
        CREATE TABLE vec_facts (
            rowid INTEGER PRIMARY KEY,
            embedding BLOB
        )
    """)
    yield conn
    conn.close()


def _insert_crystal(
    conn: sqlite3.Connection,
    fact_id: str,
    content: str,
    age_days: float = 30.0,
    is_diamond: bool = False,
    recall_count: int = 0,
    embedding: list[float] | None = None,
    project: str = "autodidact_knowledge",
) -> None:
    """Helper to insert a test crystal."""
    timestamp = time.time() - (age_days * 86400)
    meta = json.dumps({"access_stats": {"total_access_count": recall_count}})
    emb = embedding or [0.1, 0.2, 0.3, 0.4]
    emb_bytes = np.array(emb, dtype=np.float32).tobytes()

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO facts_meta (id, tenant_id, project_id, content, timestamp,
                                is_diamond, metadata)
        VALUES (?, 'sovereign', ?, ?, ?, ?, ?)
        """,
        (fact_id, project, content, timestamp, int(is_diamond), meta),
    )
    rowid = cursor.lastrowid
    cursor.execute(
        "INSERT INTO vec_facts(rowid, embedding) VALUES (?, ?)",
        (rowid, emb_bytes),
    )
    conn.commit()


# ── Temperature Tests ─────────────────────────────────────────────────────


class TestTemperature:
    """Test temperature calculation."""

    def test_hot_crystal(self) -> None:
        temp = calculate_temperature(recall_count=10, age_days=2.0)
        assert temp == pytest.approx(5.0)
        assert temp >= TEMPERATURE_HOT

    def test_cold_crystal(self) -> None:
        temp = calculate_temperature(recall_count=0, age_days=100.0)
        assert temp == 0.0
        assert temp < TEMPERATURE_COLD

    def test_warm_crystal(self) -> None:
        temp = calculate_temperature(recall_count=1, age_days=5.0)
        assert temp == pytest.approx(0.2)

    def test_new_crystal_warm_start(self) -> None:
        temp = calculate_temperature(recall_count=0, age_days=0.0)
        assert temp == 0.5  # Warm start for new crystals

    def test_new_crystal_with_recall(self) -> None:
        temp = calculate_temperature(recall_count=3, age_days=0.0)
        assert temp == 3.0


# ── Resonance Tests ───────────────────────────────────────────────────────


class TestResonance:
    @pytest.mark.asyncio
    async def test_identical_vectors(self) -> None:
        vec = [1.0, 0.0, 0.0, 0.0]
        res = await calculate_resonance(vec, [vec])
        assert res == pytest.approx(1.0, abs=0.001)

    @pytest.mark.asyncio
    async def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0, 0.0]
        res = await calculate_resonance(a, [b])
        assert res == pytest.approx(0.0, abs=0.001)

    @pytest.mark.asyncio
    async def test_best_axiom_wins(self) -> None:
        content = [1.0, 0.5, 0.0, 0.0]
        axiom_low = [0.0, 0.0, 1.0, 0.0]
        axiom_high = [0.9, 0.4, 0.0, 0.0]
        res = await calculate_resonance(content, [axiom_low, axiom_high])
        assert res > 0.9  # Should match axiom_high

    @pytest.mark.asyncio
    async def test_empty_inputs(self) -> None:
        assert await calculate_resonance([], [[1.0]]) == 0.0
        assert await calculate_resonance([1.0], []) == 0.0


# ── Quadrant Tests ────────────────────────────────────────────────────────


class TestQuadrantClassification:
    def test_active_quadrant(self) -> None:
        assert classify_quadrant(0.5, 0.7) == "ACTIVE"

    def test_foundational_quadrant(self) -> None:
        assert classify_quadrant(0.001, 0.8) == "FOUNDATIONAL"

    def test_noise_quadrant(self) -> None:
        assert classify_quadrant(0.5, 0.1) == "NOISE"

    def test_dead_weight_quadrant(self) -> None:
        assert classify_quadrant(0.001, 0.05) == "DEAD_WEIGHT"


# ── Recommendation Tests ─────────────────────────────────────────────────


class TestRecommendation:
    def test_purge_dead_weight(self) -> None:
        rec = determine_recommendation("DEAD_WEIGHT", False, 20.0, 0.001, 0.05)
        assert rec == "PURGE"

    def test_diamond_immune_to_purge(self) -> None:
        rec = determine_recommendation("DEAD_WEIGHT", True, 20.0, 0.001, 0.05)
        assert rec == "DECAY"  # Never PURGE a diamond

    def test_young_crystal_immune_to_purge(self) -> None:
        rec = determine_recommendation("DEAD_WEIGHT", False, 3.0, 0.001, 0.05)
        assert rec == "DECAY"  # Too young to purge

    def test_promote_active_crystal(self) -> None:
        rec = determine_recommendation("ACTIVE", False, 10.0, 0.5, 0.7)
        assert rec == "PROMOTE"

    def test_protect_foundational(self) -> None:
        rec = determine_recommendation("FOUNDATIONAL", False, 10.0, 0.001, 0.8)
        assert rec == "PROTECT"

    def test_noise_decays(self) -> None:
        rec = determine_recommendation("NOISE", False, 10.0, 0.5, 0.1)
        assert rec == "DECAY"


# ── Measure Crystal Sync Tests ────────────────────────────────────────────


class TestMeasureCrystalSync:
    def test_full_assessment(self) -> None:
        vitals = measure_crystal_sync(
            fact_id="test-1",
            content="How to deploy to Cloud Run with zero downtime",
            recall_count=10,
            age_days=10.0,
            is_diamond=False,
            resonance=0.7,
        )
        assert vitals.temperature == pytest.approx(1.0)
        assert vitals.resonance == 0.7
        assert vitals.quadrant == "ACTIVE"
        assert vitals.recommendation == "PROMOTE"

    def test_dead_weight_crystal(self) -> None:
        vitals = measure_crystal_sync(
            fact_id="test-2",
            content="Random outdated reference",
            recall_count=0,
            age_days=30.0,
            is_diamond=False,
            resonance=0.1,
        )
        assert vitals.quadrant == "DEAD_WEIGHT"
        assert vitals.recommendation == "PURGE"


# ── Consolidation Result Tests ────────────────────────────────────────────


class TestConsolidationResult:
    def test_total_actions(self) -> None:
        result = ConsolidationResult(purged=2, merged=1, promoted=3)
        assert result.total_actions == 6

    def test_to_dict(self) -> None:
        result = ConsolidationResult(purged=1, merged=0, promoted=2, total_scanned=10)
        d = result.to_dict()
        assert d["purged"] == 1
        assert d["promoted"] == 2
        assert d["total_actions"] == 3


# ── Cold Purge Integration Tests ──────────────────────────────────────────


class TestColdPurge:
    def test_purges_dead_weight(self, in_memory_db) -> None:
        _insert_crystal(in_memory_db, "dead-1", "obsolete info", age_days=30, recall_count=0)

        vitals = [
            CrystalVitals(
                fact_id="dead-1",
                content_preview="obsolete info",
                temperature=0.0,
                resonance=0.05,
                quadrant="DEAD_WEIGHT",
                recommendation="PURGE",
                age_days=30,
                recall_count=0,
                is_diamond=False,
            )
        ]

        result = ConsolidationResult()
        _execute_cold_purge(in_memory_db, vitals, result, dry_run=False)

        assert result.purged == 1
        # Verify actually deleted from DB
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM facts_meta WHERE id = 'dead-1'")
        assert cursor.fetchone()[0] == 0

    def test_dry_run_preserves(self, in_memory_db) -> None:
        _insert_crystal(in_memory_db, "dead-2", "obsolete info", age_days=30)

        vitals = [
            CrystalVitals(
                fact_id="dead-2",
                content_preview="obsolete info",
                temperature=0.0,
                resonance=0.05,
                quadrant="DEAD_WEIGHT",
                recommendation="PURGE",
                age_days=30,
                recall_count=0,
                is_diamond=False,
            )
        ]

        result = ConsolidationResult()
        _execute_cold_purge(in_memory_db, vitals, result, dry_run=True)

        assert result.purged == 1
        # Verify NOT deleted
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM facts_meta WHERE id = 'dead-2'")
        assert cursor.fetchone()[0] == 1

    def test_diamond_immune(self, in_memory_db) -> None:
        _insert_crystal(in_memory_db, "diamond-1", "axiom", age_days=30, is_diamond=True)

        vitals = [
            CrystalVitals(
                fact_id="diamond-1",
                content_preview="axiom",
                temperature=0.0,
                resonance=0.05,
                quadrant="DEAD_WEIGHT",
                recommendation="DECAY",  # Diamonds never get PURGE
                age_days=30,
                recall_count=0,
                is_diamond=True,
            )
        ]

        result = ConsolidationResult()
        _execute_cold_purge(in_memory_db, vitals, result, dry_run=False)

        assert result.purged == 0


# ── Diamond Promotion Integration Tests ───────────────────────────────────


class TestDiamondPromotion:
    def test_promotes_qualifying_crystal(self, in_memory_db) -> None:
        _insert_crystal(in_memory_db, "hot-1", "active knowledge", age_days=10, recall_count=20)

        vitals = [
            CrystalVitals(
                fact_id="hot-1",
                content_preview="active knowledge",
                temperature=2.0,
                resonance=0.7,
                quadrant="ACTIVE",
                recommendation="PROMOTE",
                age_days=10,
                recall_count=20,
                is_diamond=False,
            )
        ]

        result = ConsolidationResult()
        _execute_diamond_promotion(in_memory_db, vitals, result, dry_run=False)

        assert result.promoted == 1
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT is_diamond FROM facts_meta WHERE id = 'hot-1'")
        assert cursor.fetchone()[0] == 1


# ── Full Consolidation E2E Tests ──────────────────────────────────────────


class TestFullConsolidation:
    @pytest.mark.asyncio
    async def test_consolidation_with_mixed_crystals(self, in_memory_db) -> None:
        """End-to-end: mix of dead, active, and similar crystals."""
        # Dead weight — should be purged
        _insert_crystal(in_memory_db, "dead-e2e", "obsolete", age_days=30, recall_count=0)
        # Active — should be promoted
        _insert_crystal(in_memory_db, "hot-e2e", "valuable", age_days=10, recall_count=20)

        vitals = [
            CrystalVitals(
                fact_id="dead-e2e",
                content_preview="obsolete",
                temperature=0.0,
                resonance=0.05,
                quadrant="DEAD_WEIGHT",
                recommendation="PURGE",
                age_days=30,
                recall_count=0,
                is_diamond=False,
            ),
            CrystalVitals(
                fact_id="hot-e2e",
                content_preview="valuable",
                temperature=2.0,
                resonance=0.7,
                quadrant="ACTIVE",
                recommendation="PROMOTE",
                age_days=10,
                recall_count=20,
                is_diamond=False,
            ),
        ]

        result = await consolidate(in_memory_db, vitals)
        assert result.purged == 1
        assert result.promoted == 1

    @pytest.mark.asyncio
    async def test_empty_vitals(self, in_memory_db) -> None:
        result = await consolidate(in_memory_db, [])
        assert result.total_actions == 0

    @pytest.mark.asyncio
    async def test_dry_run_no_side_effects(self, in_memory_db) -> None:
        _insert_crystal(in_memory_db, "dry-1", "should survive", age_days=30)

        vitals = [
            CrystalVitals(
                fact_id="dry-1",
                content_preview="should survive",
                temperature=0.0,
                resonance=0.05,
                quadrant="DEAD_WEIGHT",
                recommendation="PURGE",
                age_days=30,
                recall_count=0,
                is_diamond=False,
            )
        ]

        result = await consolidate(in_memory_db, vitals, dry_run=True)
        assert result.purged == 1
        assert result.dry_run is True

        # Crystal should still exist
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM facts_meta WHERE id = 'dry-1'")
        assert cursor.fetchone()[0] == 1
