"""Tests for fact validation gates and CLI purge commands."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cortex.cli import cli
from cortex.engine import CortexEngine


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path):
    """Create a temp database with diverse test data."""
    path = tmp_path / "test.db"
    engine = CortexEngine(db_path=path)
    engine.init_db_sync()
    # Valid facts
    engine.store_sync("proj", "This is a valid knowledge fact for testing", fact_type="knowledge")
    engine.store_sync("proj", "Another valid fact with enough length", fact_type="decision")
    engine.store_sync("proj", "A third fact to have data to work with", fact_type="error")
    # Duplicate
    engine.store_sync("proj", "This is a valid knowledge fact for testing", fact_type="knowledge")
    engine.close_sync()
    return str(path)


# ─── FactManager.store validation tests ──────────────────────


class TestStoreValidation:
    """Tests for the new validation gates in FactManager.store."""

    def test_reject_short_content(self, tmp_path):
        path = tmp_path / "test.db"
        engine = CortexEngine(db_path=path)
        engine.init_db_sync()
        from cortex.facts.manager import FactManager

        FactManager.MIN_CONTENT_LENGTH = 20
        with pytest.raises(ValueError, match="content too short"):
            engine.store_sync("proj", "too short")
        engine.close_sync()

    def test_reject_empty_content(self, tmp_path):
        path = tmp_path / "test.db"
        engine = CortexEngine(db_path=path)
        engine.init_db_sync()
        with pytest.raises(ValueError, match="content cannot be empty"):
            engine.store_sync("proj", "")
        engine.close_sync()

    def test_reject_empty_project(self, tmp_path):
        path = tmp_path / "test.db"
        engine = CortexEngine(db_path=path)
        engine.init_db_sync()
        with pytest.raises(ValueError, match="project cannot be empty"):
            engine.store_sync("", "Valid content that is long enough")
        engine.close_sync()

    def test_dedup_returns_existing_id(self, tmp_path):
        path = tmp_path / "test.db"
        engine = CortexEngine(db_path=path)
        engine.init_db_sync()
        content = "This is a unique fact for dedup testing purposes"
        id1 = engine.store_sync("proj", content)
        id2 = engine.store_sync("proj", content)
        assert id1 == id2, "Duplicate content should return existing fact ID"
        engine.close_sync()

    def test_dedup_different_projects_are_separate(self, tmp_path):
        path = tmp_path / "test.db"
        engine = CortexEngine(db_path=path)
        engine.init_db_sync()
        content = "Shared content across different projects"
        id1 = engine.store_sync("proj-a", content)
        id2 = engine.store_sync("proj-b", content)
        assert id1 != id2, "Same content in different projects should create separate facts"
        engine.close_sync()

    def test_sanitize_double_decision_prefix(self, tmp_path):
        path = tmp_path / "test.db"
        engine = CortexEngine(db_path=path)
        engine.init_db_sync()
        fact_id = engine.store_sync(
            "proj",
            "DECISION: DECISION: Use SQLite for local storage",
            fact_type="decision",
        )
        conn = engine._get_sync_conn()
        row = conn.execute("SELECT content FROM facts WHERE id = ?", (fact_id,)).fetchone()
        assert row[0] == "DECISION: Use SQLite for local storage"
        assert "DECISION: DECISION:" not in row[0]
        conn.close()
        engine.close_sync()


# ─── CLI purge command tests ──────────────────────


class TestPurgeDuplicates:
    def test_purge_duplicates_dry_run(self, runner, db_path):
        result = runner.invoke(cli, ["purge", "duplicates", "--dry-run", "--db", db_path])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output or "No duplicates" in result.output

    def test_purge_duplicates_execute(self, runner, db_path):
        result = runner.invoke(cli, ["purge", "duplicates", "--db", db_path])
        assert result.exit_code == 0


class TestPurgeEmpty:
    def test_purge_empty_dry_run(self, runner, db_path):
        result = runner.invoke(cli, ["purge", "empty", "--dry-run", "--db", db_path])
        assert result.exit_code == 0

    def test_purge_empty_execute(self, runner, db_path):
        result = runner.invoke(cli, ["purge", "empty", "--db", db_path])
        assert result.exit_code == 0


class TestPurgeProject:
    def test_purge_project_dry_run(self, runner, db_path):
        result = runner.invoke(cli, ["purge", "project", "proj", "--dry-run", "--db", db_path])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_purge_project_execute(self, runner, db_path, monkeypatch, tmp_path):
        result = runner.invoke(cli, ["purge", "project", "proj", "--db", db_path])
        assert result.exit_code == 0
        assert "Deprecated" in result.output

    def test_purge_nonexistent_project(self, runner, db_path):
        result = runner.invoke(cli, ["purge", "project", "nonexistent", "--db", db_path])
        assert result.exit_code == 0
        assert "No active facts" in result.output
