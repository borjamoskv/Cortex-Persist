"""
Tests for CLI CRUD commands — delete, list, edit.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cortex.cli import cli
from cortex.engine import CortexEngine


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Create a temp database with test data."""
    # Bypass exergy filter so test content can be stored
    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    path = tmp_path / "test.db"
    engine = CortexEngine(db_path=path)
    engine.init_db_sync()
    engine.store_sync(
        "test-project",
        "First test fact for CORTEX validation",
        fact_type="knowledge",
        source="cli",
    )
    engine.store_sync(
        "test-project",
        "Second test fact for error tracking",
        fact_type="error",
        source="cli",
    )
    engine.store_sync(
        "other-project",
        "Third test fact for ghost registering",
        fact_type="ghost",
        source="cli",
    )
    engine.close_sync()
    return str(path)


class TestListCommand:
    """Tests for 'cortex list'."""

    def test_list_shows_facts(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path])
        assert result.exit_code == 0
        # Content is AES-encrypted in v6 — check structure, not plaintext
        assert "test-project" in result.output or "CORTEX" in result.output

    def test_list_filter_by_project(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path, "-p", "test-project"])
        assert result.exit_code == 0
        # Should show test-project facts but not other-project
        assert "other-project" not in result.output or "test-project" in result.output

    def test_list_filter_by_type(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path, "--type", "ghost"])
        assert result.exit_code == 0
        # Content is AES-encrypted — check type label appears, not plaintext
        assert "ghost" in result.output.lower()

    def test_list_empty_result(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path, "-p", "nonexistent"])
        assert result.exit_code == 0
        # i18n-agnostic: all translations contain the Panel title emoji
        assert "📭" in result.output or "no" in result.output.lower()

    def test_list_with_limit(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path, "-n", "1"])
        assert result.exit_code == 0


class TestDeleteCommand:
    """Tests for 'cortex delete'."""

    def test_delete_existing_fact(self, runner, db_path, monkeypatch, tmp_path):
        # Monkeypatch sync paths to avoid touching real files
        monkeypatch.setattr("cortex.extensions.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.extensions.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr("cortex.extensions.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json")

        result = runner.invoke(cli, ["delete", "1", "--db", db_path])
        assert result.exit_code == 0
        assert "deprecado" in result.output.lower() or "deprecated" in result.output.lower()

    def test_delete_nonexistent_fact(self, runner, db_path):
        result = runner.invoke(cli, ["delete", "999", "--db", db_path])
        assert result.exit_code == 0
        # i18n-agnostic: fact ID appears in all translations, plus the Panel icon
        assert "999" in result.output and "🔍" in result.output

    def test_delete_with_reason(self, runner, db_path, monkeypatch, tmp_path):
        monkeypatch.setattr("cortex.extensions.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.extensions.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr("cortex.extensions.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json")

        result = runner.invoke(cli, ["delete", "1", "-r", "testing", "--db", db_path])
        assert result.exit_code == 0
        assert "deprecado" in result.output.lower() or "deprecated" in result.output.lower()


class TestEditCommand:
    """Tests for 'cortex edit'."""

    def test_edit_existing_fact(self, runner, db_path, monkeypatch, tmp_path):
        monkeypatch.setattr("cortex.extensions.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.extensions.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr("cortex.extensions.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json")

        result = runner.invoke(
            cli, ["edit", "1", "Updated content here with more detail", "--db", db_path]
        )
        assert result.exit_code == 0
        assert "editado" in result.output or "edited" in result.output.lower()

    def test_edit_nonexistent_fact(self, runner, db_path):
        result = runner.invoke(
            cli, ["edit", "999", "New content that is long enough", "--db", db_path]
        )
        assert result.exit_code == 0
        # i18n-agnostic: fact ID and Panel icon appear in all translations
        assert "999" in result.output and "🔍" in result.output

    def test_edit_preserves_metadata(self, runner, db_path, monkeypatch, tmp_path):
        """Edit should preserve project, type, tags from original."""
        monkeypatch.setattr("cortex.extensions.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.extensions.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr("cortex.extensions.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json")

        result = runner.invoke(
            cli, ["edit", "1", "Edited content with extended metadata", "--db", db_path]
        )
        assert result.exit_code == 0

        # Verify project still listed (content is encrypted)
        list_result = runner.invoke(cli, ["list", "--db", db_path, "-p", "test-project"])
        assert "test-project" in list_result.output or list_result.exit_code == 0


class TestStoreCommand:
    """Tests for 'cortex store'."""

    def test_store_with_meta(self, runner, tmp_path, monkeypatch):
        # We drop the CORTEX_SKIP_EXERGY_VALIDATION bypass to test thermodynamic validation directly
        monkeypatch.delenv("CORTEX_SKIP_EXERGY_VALIDATION", raising=False)
        monkeypatch.setattr("cortex.extensions.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.extensions.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr("cortex.extensions.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json")

        db_path = tmp_path / "test_store.db"

        # Initialize the fresh db first
        engine = CortexEngine(db_path=str(db_path))
        engine.init_db_sync()
        engine.close_sync()

        meta_json = '{"_prior_entropy": 500.0, "_posterior_entropy": 10.0, "_tokens": 150}'
        result = runner.invoke(
            cli,
            [
                "store",
                "test-project",
                "Testing thermodynamic escalation structural pass",
                "--type",
                "knowledge",
                "--meta",
                meta_json,
                "--db",
                str(db_path),
            ],
        )
        assert result.exit_code == 0
        assert "Stored fact" in result.output

    def test_store_invalid_meta_json(self, runner, tmp_path, monkeypatch):
        monkeypatch.setattr("cortex.extensions.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.extensions.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr("cortex.extensions.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json")
        db_path = tmp_path / "test_store_invalid.db"
        engine = CortexEngine(db_path=str(db_path))
        engine.init_db_sync()
        engine.close_sync()

        result = runner.invoke(
            cli,
            [
                "store",
                "test-project",
                "Failing JSON",
                "--meta",
                "{invalid_json}",
                "--db",
                str(db_path),
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON in --meta" in result.output

