"""Tests for cortex.daemon — Guard Daemon components.

Tests the ActionClassifier, VerdictEmitter, and GuardDaemon integration.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cortex.daemon.action_classifier import (
    ActionClassifier,
    ActionType,
    ClassifiedAction,
    GuardLevel,
)
from cortex.daemon.verdict_emitter import (
    GuardVerdict,
    VerdictEmitter,
)
from cortex.guards.verdicts import PolicyVerdict, VerdictReport


# ────────────────────────────────────────────────
# ActionClassifier Tests
# ────────────────────────────────────────────────


class TestActionClassifier:
    """Test the deterministic action classifier."""

    def setup_method(self) -> None:
        self.classifier = ActionClassifier()

    # --- P0 Critical: Secret Files ---

    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            ".env.local",
            ".env.production",
            "config/.env.secret",
            "certs/server.pem",
            "keys/deploy.key",
            "auth/app.p12",
        ],
    )
    def test_secret_files_p0(self, path: str) -> None:
        result = self.classifier.classify_file_event(path)
        assert result.action_type == ActionType.SECRET_ACCESS
        assert result.guard_level == GuardLevel.P0_CRITICAL

    # --- P1 High: Dependency Files ---

    @pytest.mark.parametrize(
        "path",
        [
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "Cargo.toml",
            "go.mod",
        ],
    )
    def test_dep_files_p1(self, path: str) -> None:
        result = self.classifier.classify_file_event(path)
        assert result.action_type == ActionType.DEP_CHANGE
        assert result.guard_level == GuardLevel.P1_HIGH

    # --- P2 Advisory: Lock Files ---

    @pytest.mark.parametrize(
        "path",
        [
            "Cargo.lock",
            "yarn.lock",
            "package-lock.json",
        ],
    )
    def test_lock_files_p2(self, path: str) -> None:
        result = self.classifier.classify_file_event(path)
        assert result.action_type == ActionType.DEP_CHANGE
        assert result.guard_level == GuardLevel.P2_ADVISORY

    # --- P1 High: Migration Files ---

    @pytest.mark.parametrize(
        "path",
        [
            "alembic/versions/001_init.py",
            "cortex/migrations/0002_add_vec.py",
            "db/migrate/20240101_create_users.sql",
        ],
    )
    def test_migration_files_p1(self, path: str) -> None:
        result = self.classifier.classify_file_event(path)
        assert result.action_type == ActionType.MIGRATION
        assert result.guard_level == GuardLevel.P1_HIGH

    # --- P2 Advisory: Code Files ---

    @pytest.mark.parametrize(
        "path",
        [
            "cortex/engine/store.py",
            "src/app.tsx",
            "main.rs",
            "handler.go",
            "contracts/Vault.sol",
        ],
    )
    def test_code_files_p2(self, path: str) -> None:
        result = self.classifier.classify_file_event(path)
        assert result.action_type == ActionType.CODE_MUTATION
        assert result.guard_level == GuardLevel.P2_ADVISORY

    # --- P2 Advisory: Config Files ---

    @pytest.mark.parametrize(
        "path",
        [
            "config.yaml",
            "settings.toml",
            "app.json",
        ],
    )
    def test_config_files_p2(self, path: str) -> None:
        result = self.classifier.classify_file_event(path)
        assert result.action_type == ActionType.CONFIG_CHANGE
        assert result.guard_level == GuardLevel.P2_ADVISORY

    # --- Passthrough: Ignored Patterns ---

    @pytest.mark.parametrize(
        "path",
        [
            "__pycache__/module.pyc",
            ".git/objects/abc123",
            "node_modules/react/index.js",
            ".venv/lib/python3.12/site.py",
        ],
    )
    def test_ignored_patterns_passthrough(self, path: str) -> None:
        result = self.classifier.classify_file_event(path)
        assert result.guard_level == GuardLevel.PASSTHROUGH

    # --- Passthrough: Compiled Files ---

    def test_compiled_files_passthrough(self) -> None:
        result = self.classifier.classify_file_event("module.pyc")
        assert result.action_type == ActionType.READ_ONLY
        assert result.guard_level == GuardLevel.PASSTHROUGH

    # --- Command Classification ---

    def test_safe_command_passthrough(self) -> None:
        result = self.classifier.classify_command("git status")
        assert result.action_type == ActionType.READ_ONLY
        assert result.guard_level == GuardLevel.PASSTHROUGH

    def test_destructive_command_p0(self) -> None:
        result = self.classifier.classify_command("rm -rf /")
        assert result.action_type == ActionType.DESTRUCTIVE_CMD
        assert result.guard_level == GuardLevel.P0_CRITICAL

    def test_install_command_p1(self) -> None:
        result = self.classifier.classify_command("pip install requests")
        assert result.action_type == ActionType.DEP_CHANGE
        assert result.guard_level == GuardLevel.P1_HIGH

    def test_unknown_command_p2(self) -> None:
        result = self.classifier.classify_command("./deploy.sh production")
        assert result.action_type == ActionType.CODE_MUTATION
        assert result.guard_level == GuardLevel.P2_ADVISORY


# ────────────────────────────────────────────────
# VerdictEmitter Tests
# ────────────────────────────────────────────────


class TestVerdictEmitter:
    """Test the multi-output verdict emitter."""

    def _make_verdict(
        self,
        verdict: PolicyVerdict = PolicyVerdict.CORTEX_PASS,
        action_type: ActionType = ActionType.CODE_MUTATION,
        guard_level: GuardLevel = GuardLevel.P2_ADVISORY,
    ) -> GuardVerdict:
        action = ClassifiedAction(
            action_type=action_type,
            guard_level=guard_level,
            path="/test/file.py",
            detail="test detail",
        )
        report = VerdictReport(verdict=verdict, rule_id="TEST-001")
        return GuardVerdict(action=action, report=report)

    def test_counters_pass(self) -> None:
        emitter = VerdictEmitter(terminal=False, logfile=None, quiet=True)
        verdict = self._make_verdict(PolicyVerdict.CORTEX_PASS)
        emitter.emit(verdict)
        assert emitter.total_pass == 1
        assert emitter.total_warn == 0
        assert emitter.total_block == 0

    def test_counters_warn(self) -> None:
        emitter = VerdictEmitter(terminal=False, logfile=None, quiet=True)
        verdict = self._make_verdict(PolicyVerdict.CORTEX_WARN)
        emitter.emit(verdict)
        assert emitter.total_warn == 1

    def test_counters_block(self) -> None:
        emitter = VerdictEmitter(terminal=False, logfile=None, quiet=True)
        verdict = self._make_verdict(PolicyVerdict.CORTEX_BLOCK)
        emitter.emit(verdict)
        assert emitter.total_block == 1

    def test_passthrough_counter(self) -> None:
        emitter = VerdictEmitter(terminal=False, logfile=None, quiet=True)
        verdict = self._make_verdict(
            PolicyVerdict.CORTEX_PASS,
            guard_level=GuardLevel.PASSTHROUGH,
        )
        emitter.emit(verdict)
        assert emitter.total_passthrough == 1
        assert emitter.total_pass == 0

    def test_logfile_output(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".log", mode="w", delete=False) as f:
            log_path = Path(f.name)

        try:
            emitter = VerdictEmitter(
                terminal=False,
                logfile=log_path,
                quiet=True,
            )
            verdict = self._make_verdict(PolicyVerdict.CORTEX_BLOCK)
            emitter.emit(verdict)

            content = log_path.read_text(encoding="utf-8").strip()
            entry = json.loads(content)
            assert entry["verdict"] == "CORTEX_BLOCK"
            assert entry["rule_id"] == "TEST-001"
            assert entry["action_type"] == "code_mutation"
        finally:
            log_path.unlink(missing_ok=True)

    def test_history_ring_buffer(self) -> None:
        emitter = VerdictEmitter(terminal=False, logfile=None, quiet=True)
        for _ in range(10):
            emitter.emit(self._make_verdict())
        assert len(emitter.recent_verdicts) == 10
        assert emitter.stats["total"] == 10

    def test_stats(self) -> None:
        emitter = VerdictEmitter(terminal=False, logfile=None, quiet=True)
        emitter.emit(self._make_verdict(PolicyVerdict.CORTEX_PASS))
        emitter.emit(self._make_verdict(PolicyVerdict.CORTEX_WARN))
        emitter.emit(self._make_verdict(PolicyVerdict.CORTEX_BLOCK))
        stats = emitter.stats
        assert stats["pass"] == 1
        assert stats["warn"] == 1
        assert stats["block"] == 1
        assert stats["total"] == 3

    def test_verdict_to_json(self) -> None:
        verdict = self._make_verdict(PolicyVerdict.CORTEX_BLOCK)
        data = json.loads(verdict.to_json())
        assert "verdict" in data
        assert "timestamp" in data
        assert "path" in data


# ────────────────────────────────────────────────
# GuardDaemon Integration Tests
# ────────────────────────────────────────────────


class TestGuardDaemon:
    """Test the Guard Daemon core logic (not the watcher loop)."""

    def test_process_file_event_p0_block(self) -> None:
        from cortex.daemon.guard_daemon import GuardDaemon

        daemon = GuardDaemon(quiet=True)
        daemon._init_components()

        verdict = daemon.process_file_event(".env")
        assert verdict is not None
        assert verdict.is_block
        assert verdict.action.guard_level == GuardLevel.P0_CRITICAL

    def test_process_file_event_code_pass(self) -> None:
        from cortex.daemon.guard_daemon import GuardDaemon

        daemon = GuardDaemon(quiet=True)
        daemon._init_components()

        verdict = daemon.process_file_event("cortex/engine/store.py")
        assert verdict is not None
        assert verdict.action.action_type == ActionType.CODE_MUTATION

    def test_process_file_event_ignored(self) -> None:
        from cortex.daemon.guard_daemon import GuardDaemon

        daemon = GuardDaemon(quiet=True)
        daemon._init_components()

        verdict = daemon.process_file_event("__pycache__/cache.pyc")
        assert verdict is not None
        assert verdict.action.guard_level == GuardLevel.PASSTHROUGH

    def test_debounce(self) -> None:
        from cortex.daemon.guard_daemon import GuardDaemon

        daemon = GuardDaemon(quiet=True)
        daemon._init_components()

        # First call should work
        v1 = daemon.process_file_event("test.py")
        assert v1 is not None

        # Immediate second call should be debounced
        v2 = daemon.process_file_event("test.py")
        assert v2 is None

    def test_pid_management(self) -> None:
        from cortex.daemon.guard_daemon import GuardDaemon

        with tempfile.NamedTemporaryFile(suffix=".pid", delete=False) as f:
            pid_path = Path(f.name)

        try:
            daemon = GuardDaemon(pid_file=pid_path, quiet=True)
            daemon._write_pid()

            pid = GuardDaemon.read_pid(pid_path)
            assert pid is not None
            assert pid > 0

            daemon._cleanup_pid()
            assert not pid_path.exists()
        finally:
            pid_path.unlink(missing_ok=True)

    def test_is_daemon_running_false(self) -> None:
        from cortex.daemon.guard_daemon import GuardDaemon

        # No PID file -> not running
        fake_pid = Path("/tmp/cortex_test_nonexistent.pid")
        assert not GuardDaemon.is_daemon_running(fake_pid)

    def test_guard_daemon_ledger_persistence(self, tmp_path: Path) -> None:
        from cortex.daemon.guard_daemon import GuardDaemon
        import sqlite3
        import json

        db_path = str(tmp_path / "test_ledger.db")

        # Initialize the ledger database schema by using SovereignLedger
        from cortex.ledger.ledger_core import SovereignLedger

        conn = sqlite3.connect(db_path)
        ledger = SovereignLedger(conn)
        conn.close()

        # Instantiate daemon with this database
        daemon = GuardDaemon(quiet=True, ledger_db=db_path)
        daemon._load_policy()
        daemon._init_components()

        # Trigger a warn/block event, e.g. modification of requirements.txt
        verdict = daemon.process_file_event("requirements.txt")
        assert verdict is not None
        assert verdict.report.verdict.value == "CORTEX_WARN"

        # Connect to DB and inspect the transactions table
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, action, detail FROM transactions WHERE action = 'GUARD_VERDICT'")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        tx_id, action, detail_str = rows[0]
        assert action == "GUARD_VERDICT"
        detail = json.loads(detail_str)
        assert detail["verdict"] == "CORTEX_WARN"
        assert detail["target"] == "requirements.txt"
        assert detail["action_type"] == "dep_change"

    def test_guard_daemon_rollback_snapshots(self, monkeypatch) -> None:
        from cortex.daemon.guard_daemon import GuardDaemon

        daemon = GuardDaemon(quiet=True)
        daemon._load_policy()
        daemon._init_components()

        # Mock the create_snapshot method on self._rollback_spine
        called_args = []

        def mock_create_snapshot(action_type: str, reason: str) -> dict:
            called_args.append((action_type, reason))
            return {}

        monkeypatch.setattr(daemon._rollback_spine, "create_snapshot", mock_create_snapshot)

        # Trigger an event that triggers "dep_change" policy matching
        verdict = daemon.process_file_event("requirements.txt")
        assert verdict is not None

        # Assert create_snapshot was called!
        assert len(called_args) == 1
        action_type, reason = called_args[0]
        assert action_type == "dep_change"
        assert "dep_change" in reason
