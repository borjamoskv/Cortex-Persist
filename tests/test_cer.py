"""Tests for CER (Cognitive Evolution Rate) — cortex evolution.

Verifies CER computation, friction detection, health classification,
and CLI commands.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from cortex.evolution.cer import (
    CERConfig,
    CERResult,
    DecisionFriction,
    _classify_health,
    _cosine_similarity,
    compute_cer,
)


# ─── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def cer_db(tmp_path: Path) -> Path:
    """Create a minimal CORTEX-compatible SQLite database with decisions."""
    db_path = tmp_path / "cer_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            fact_type TEXT NOT NULL DEFAULT 'knowledge',
            tags TEXT NOT NULL DEFAULT '[]',
            confidence TEXT NOT NULL DEFAULT 'stated',
            valid_from TEXT NOT NULL DEFAULT (datetime('now')),
            valid_until TEXT,
            source TEXT,
            meta TEXT DEFAULT '{}',
            consensus_score REAL DEFAULT 1.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            tx_id INTEGER,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            hash TEXT,
            signature TEXT,
            signer_pubkey TEXT,
            is_quarantined INTEGER NOT NULL DEFAULT 0,
            quarantined_at TEXT,
            quarantine_reason TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def cer_db_with_decisions(cer_db: Path) -> Path:
    """Populate the test database with diverse decisions."""
    conn = sqlite3.connect(str(cer_db))
    decisions = [
        ("CORTEX", "Use AES-GCM encryption for all stored facts"),
        ("CORTEX", "Implement ghost_reaper with TTL-based decay"),
        ("CORTEX", "Shannon module measures information entropy of memory"),
        ("CORTEX", "Policy engine uses Bellman value function for prioritization"),
        ("CORTEX", "Continuity monitor tracks cognitive gaps between invocations"),
        ("NotchLive", "Use AppKit instead of SwiftUI for notch rendering"),
        ("NotchLive", "NervousSystem handles emotional state transitions"),
        ("NotchLive", "IOKit for hardware sensor integration"),
        ("naroa", "Vite SPA with Industrial Noir design system"),
        ("naroa", "Gallery uses intersection observer for lazy loading"),
    ]
    for project, content in decisions:
        conn.execute(
            "INSERT INTO facts (project, content, fact_type) VALUES (?, ?, 'decision')",
            (project, content),
        )
    conn.commit()
    conn.close()
    return cer_db


# ─── Unit Tests: Utility Functions ────────────────────────────────


class TestCosinesimilarity:
    """Test the cosine similarity function."""

    def test_identical_vectors(self):
        a = np.array([1.0, 0.0, 0.0])
        assert _cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert _cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector(self):
        a = np.array([1.0, 2.0])
        b = np.array([0.0, 0.0])
        assert _cosine_similarity(a, b) == 0.0


class TestHealthClassification:
    """Test CER health zone classification."""

    def test_stagnant(self):
        config = CERConfig()
        assert _classify_health(0.0, config) == "stagnant"
        assert _classify_health(0.10, config) == "stagnant"
        assert _classify_health(0.14, config) == "stagnant"

    def test_evolving(self):
        config = CERConfig()
        assert _classify_health(0.15, config) == "evolving"
        assert _classify_health(0.25, config) == "evolving"
        assert _classify_health(0.35, config) == "evolving"

    def test_chaotic(self):
        config = CERConfig()
        assert _classify_health(0.36, config) == "chaotic"
        assert _classify_health(0.50, config) == "chaotic"
        assert _classify_health(1.0, config) == "chaotic"

    def test_custom_config(self):
        config = CERConfig(sweet_spot_low=0.1, sweet_spot_high=0.5)
        assert _classify_health(0.09, config) == "stagnant"
        assert _classify_health(0.10, config) == "evolving"
        assert _classify_health(0.50, config) == "evolving"
        assert _classify_health(0.51, config) == "chaotic"


# ─── Unit Tests: Data Models ─────────────────────────────────────


class TestDataModels:
    """Test CER dataclasses."""

    def test_config_defaults(self):
        config = CERConfig()
        assert config.sweet_spot_low == 0.15
        assert config.sweet_spot_high == 0.35
        assert config.max_decisions == 50
        assert config.surprise_threshold == 0.55

    def test_friction_creation(self):
        friction = DecisionFriction(
            fact_id=42,
            project="CORTEX",
            content="Test decision",
            surprise_score=0.65,
            age_days=3.5,
        )
        assert friction.fact_id == 42
        assert friction.surprise_score == 0.65
        assert friction.fact_type == "decision"

    def test_result_properties(self):
        result = CERResult(
            cer=0.25,
            total_decisions=20,
            discrepancies=5,
            health="evolving",
        )
        assert result.health_icon == "🌱"
        assert result.health_color == "green"

    def test_result_stagnant_properties(self):
        result = CERResult(
            cer=0.0,
            total_decisions=0,
            discrepancies=0,
            health="stagnant",
        )
        assert result.health_icon == "🧊"
        assert result.health_color == "cyan"

    def test_result_chaotic_properties(self):
        result = CERResult(
            cer=0.8,
            total_decisions=10,
            discrepancies=8,
            health="chaotic",
        )
        assert result.health_icon == "🌋"
        assert result.health_color == "red"


# ─── Integration Tests: CER Computation ──────────────────────────


@pytest.mark.asyncio()
class TestComputeCER:
    """Test compute_cer against a real SQLite database."""

    async def test_empty_db(self, cer_db: Path):
        """No decisions → CER = 0, health = stagnant."""
        from cortex.engine import CortexEngine

        engine = CortexEngine(db_path=cer_db)
        try:
            await engine.init_db()
            result = await compute_cer(engine)

            assert result.cer == 0.0
            assert result.total_decisions == 0
            assert result.discrepancies == 0
            assert result.health == "stagnant"
            assert result.frictions == []
        finally:
            await engine.close()

    async def test_with_decisions(self, cer_db_with_decisions: Path):
        """Diverse decisions should produce a non-zero CER."""
        from cortex.engine import CortexEngine

        engine = CortexEngine(db_path=cer_db_with_decisions)
        try:
            await engine.init_db()
            result = await compute_cer(engine)

            assert result.total_decisions == 10
            assert 0.0 <= result.cer <= 1.0
            assert result.centroid_norm > 0
            assert result.health in {"stagnant", "evolving", "chaotic"}
        finally:
            await engine.close()

    async def test_project_scoping(self, cer_db_with_decisions: Path):
        """Scoping to a project should only analyze that project's decisions."""
        from cortex.engine import CortexEngine

        engine = CortexEngine(db_path=cer_db_with_decisions)
        try:
            await engine.init_db()
            result = await compute_cer(engine, project="CORTEX")

            assert result.total_decisions == 5
        finally:
            await engine.close()

    async def test_frictions_sorted_by_surprise(self, cer_db_with_decisions: Path):
        """Frictions should be sorted highest surprise first."""
        from cortex.engine import CortexEngine

        engine = CortexEngine(db_path=cer_db_with_decisions)
        try:
            await engine.init_db()
            result = await compute_cer(engine)

            if len(result.frictions) >= 2:
                scores = [f.surprise_score for f in result.frictions]
                assert scores == sorted(scores, reverse=True)
        finally:
            await engine.close()

    async def test_config_override(self, cer_db_with_decisions: Path):
        """Custom config should change friction detection threshold."""
        from cortex.engine import CortexEngine

        engine = CortexEngine(db_path=cer_db_with_decisions)
        try:
            await engine.init_db()

            # Very strict threshold → more frictions
            strict = CERConfig(surprise_threshold=0.95)
            result_strict = await compute_cer(engine, config=strict)

            # Very lenient threshold → fewer frictions
            lenient = CERConfig(surprise_threshold=0.1)
            result_lenient = await compute_cer(engine, config=lenient)

            assert result_strict.discrepancies >= result_lenient.discrepancies
        finally:
            await engine.close()


# ─── CLI Tests ────────────────────────────────────────────────────


class TestEvolutionCLI:
    """Test CLI commands via Click's test runner."""

    def test_status_command_exists(self):
        """Verify the evolution status command is registered."""
        from click.testing import CliRunner

        from cortex.cli.common import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["evolution", "--help"])
        assert result.exit_code == 0
        assert "evolution" in result.output.lower() or "CER" in result.output

    def test_frictions_command_exists(self):
        """Verify the evolution frictions command is registered."""
        from click.testing import CliRunner

        from cortex.cli.common import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["evolution", "frictions", "--help"])
        assert result.exit_code == 0
        assert "surprise" in result.output.lower() or "friction" in result.output.lower()
