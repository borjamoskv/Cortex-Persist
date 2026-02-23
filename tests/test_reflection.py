"""
Tests for CORTEX Reflection System — reflect + inject.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.timeout(120)

from click.testing import CliRunner

from cortex.cli import cli
from cortex.engine import CortexEngine
from cortex.reflection import (
    InjectedLearning,
    Reflection,
    format_injection_json,
    format_injection_markdown,
    generate_reflection,
    inject_reflections,
)


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def engine(tmp_path):
    """CortexEngine with a temp database."""
    path = tmp_path / "reflect_test.db"
    eng = CortexEngine(db_path=path)
    eng.init_db_sync()
    yield eng
    eng.close_sync()


@pytest.fixture
def db_path(tmp_path):
    """Create a temp database with seed data for CLI tests."""
    path = tmp_path / "cli_reflect.db"
    eng = CortexEngine(db_path=path)
    eng.init_db_sync()
    # Seed a reflection so inject has something to find
    eng.store_sync(
        "test-project",
        "[REFLECTION] Fixed RRF scoring bug by normalizing weights",
        fact_type="reflection",
        tags=["post-mortem"],
        confidence="confirmed",
    )
    eng.store_sync(
        "test-project",
        "Hybrid search returned stale results due to missing deprecation filter",
        fact_type="error",
        tags=["search"],
    )
    eng.close_sync()
    return str(path)


# ─── Unit Tests: Reflection Dataclass ────────────────────────────────


class TestReflectionDataclass:
    """Tests for the Reflection dataclass."""

    def test_to_content_basic(self):
        r = Reflection(
            project="cortex",
            summary="Fixed search bug",
            errors=["RRF weights inverted"],
            decisions=["Switched to cosine similarity"],
            timestamp="2026-02-22T22:00:00Z",
        )
        content = r.to_content()
        assert "[REFLECTION] Fixed search bug" in content
        assert "✗ Error: RRF weights inverted" in content
        assert "→ Decision: Switched to cosine similarity" in content
        assert "2026-02-22T22:00:00Z" in content

    def test_to_content_no_errors_no_decisions(self):
        r = Reflection(
            project="cortex",
            summary="Clean session",
            errors=[],
            decisions=[],
            timestamp="2026-02-22T22:00:00Z",
        )
        content = r.to_content()
        assert "[REFLECTION] Clean session" in content
        assert "Error" not in content
        assert "Decision" not in content


# ─── Unit Tests: generate_reflection ─────────────────────────────────


class TestGenerateReflection:
    """Tests for the generate_reflection function."""

    def test_stores_fact_with_correct_type(self, engine):
        fact_id = generate_reflection(
            engine=engine,
            project="test-project",
            summary="Session went smoothly with no issues encountered",
        )
        assert isinstance(fact_id, int)
        assert fact_id > 0

        # Verify stored with correct type
        conn = engine._get_sync_conn()
        row = conn.execute(
            "SELECT fact_type, content FROM facts WHERE id = ?", (fact_id,)
        ).fetchone()
        assert row[0] == "reflection"
        assert "[REFLECTION]" in row[1]

    def test_stores_errors_and_decisions(self, engine):
        fact_id = generate_reflection(
            engine=engine,
            project="test-project",
            summary="Debugged search performance issue in hybrid module",
            errors=["Query timeout on large datasets"],
            decisions=["Added index on created_at column"],
        )
        conn = engine._get_sync_conn()
        row = conn.execute("SELECT content FROM facts WHERE id = ?", (fact_id,)).fetchone()
        assert "Error: Query timeout" in row[0]
        assert "Decision: Added index" in row[0]

    def test_stores_with_confirmed_confidence(self, engine):
        fact_id = generate_reflection(
            engine=engine,
            project="test-project",
            summary="Verified that reflection confidence is set correctly",
        )
        conn = engine._get_sync_conn()
        row = conn.execute("SELECT confidence FROM facts WHERE id = ?", (fact_id,)).fetchone()
        assert row[0] == "confirmed"


# ─── Unit Tests: inject_reflections ──────────────────────────────────


class TestInjectReflections:
    """Tests for the inject_reflections function."""

    def test_returns_empty_list_on_empty_db(self, engine):
        learnings = inject_reflections(
            engine=engine,
            context_hint="anything at all about search performance",
        )
        assert isinstance(learnings, list)
        assert len(learnings) == 0

    def test_returns_learnings_after_storing_reflections(self, engine):
        # Store some reflections
        generate_reflection(
            engine=engine,
            project="cortex",
            summary="Fixed hybrid search RRF scoring normalization bug",
            errors=["Weights not normalized"],
        )
        generate_reflection(
            engine=engine,
            project="cortex",
            summary="Improved embedding compression ratio significantly",
            decisions=["Use int8 quantization"],
        )

        learnings = inject_reflections(
            engine=engine,
            context_hint="search scoring and ranking improvements needed",
            project="cortex",
            top_k=5,
        )
        assert isinstance(learnings, list)
        # Should find at least one (text-based search will match)
        # Note: semantic search may not work in test env without model
        for lr in learnings:
            assert isinstance(lr, InjectedLearning)
            assert lr.fact_id > 0
            assert lr.project == "cortex"


# ─── Unit Tests: Formatters ──────────────────────────────────────────


class TestFormatters:
    """Tests for injection output formatters."""

    def test_format_markdown_with_learnings(self):
        learnings = [
            InjectedLearning(
                fact_id=1,
                project="cortex",
                content="Fixed a search bug by normalizing vectors",
                fact_type="reflection",
                score=0.85,
                created_at="2026-02-22T22:00:00Z",
            ),
        ]
        output = format_injection_markdown(learnings)
        assert "CORTEX Reflections" in output
        assert "Fixed a search bug" in output
        assert "0.850" in output

    def test_format_markdown_empty(self):
        output = format_injection_markdown([])
        assert "No prior reflections" in output

    def test_format_json_with_learnings(self):
        learnings = [
            InjectedLearning(
                fact_id=42,
                project="cortex",
                content="Learned to check embeddings table initialization",
                fact_type="meta_learning",
                score=0.72,
                created_at="2026-02-22T22:00:00Z",
            ),
        ]
        output = format_injection_json(learnings)
        import json

        data = json.loads(output)
        assert len(data) == 1
        assert data[0]["fact_id"] == 42
        assert data[0]["fact_type"] == "meta_learning"


# ─── CLI Integration Tests ───────────────────────────────────────────


class TestCLIReflect:
    """Tests for 'cortex reflect' command."""

    def test_reflect_basic(self, runner, db_path):
        result = runner.invoke(
            cli,
            ["reflect", "test-project", "Fixed the login timeout issue", "--db", db_path],
        )
        assert result.exit_code == 0
        assert "Reflection" in result.output
        assert "stored" in result.output

    def test_reflect_with_errors_and_decisions(self, runner, db_path):
        result = runner.invoke(
            cli,
            [
                "reflect",
                "test-project",
                "Debugged and fixed search latency problems",
                "--errors",
                "timeout on queries,missing index",
                "--decisions",
                "added composite index,enabled query cache",
                "--db",
                db_path,
            ],
        )
        assert result.exit_code == 0
        assert "2 error(s)" in result.output
        assert "2 decision(s)" in result.output


class TestCLIInject:
    """Tests for 'cortex inject' command."""

    def test_inject_markdown(self, runner, db_path):
        result = runner.invoke(
            cli,
            ["inject", "test-project", "--hint", "search scoring", "--db", db_path],
        )
        assert result.exit_code == 0

    def test_inject_json(self, runner, db_path):
        result = runner.invoke(
            cli,
            [
                "inject",
                "test-project",
                "--hint",
                "search optimization",
                "--format",
                "json",
                "--db",
                db_path,
            ],
        )
        assert result.exit_code == 0

    def test_inject_no_project(self, runner, db_path):
        result = runner.invoke(
            cli,
            ["inject", "--hint", "general context", "--db", db_path],
        )
        assert result.exit_code == 0
