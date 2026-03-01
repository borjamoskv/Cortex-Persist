"""Tests for the ContinuityMonitor v2 — cognitive persistence layer."""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from cortex.daemon.monitors.continuity import (
    ContinuityAlert,
    ContinuityEvent,
    ContinuityMonitor,
    ContinuityState,
)


@pytest.fixture()
def continuity_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect continuity files to tmp_path."""
    monkeypatch.setattr(
        "cortex.daemon.monitors.continuity.CONTINUITY_DIR",
        tmp_path,
    )
    monkeypatch.setattr(
        "cortex.daemon.monitors.continuity.TIMELINE_FILE",
        tmp_path / "timeline.jsonl",
    )
    monkeypatch.setattr(
        "cortex.daemon.monitors.continuity.BRIEFING_FILE",
        tmp_path / "briefing.md",
    )
    monkeypatch.setattr(
        "cortex.daemon.monitors.continuity.STATE_FILE",
        tmp_path / "state.json",
    )
    return tmp_path


@pytest.fixture()
def fake_db(tmp_path: Path) -> Path:
    """Create a minimal CORTEX-compatible SQLite database."""
    db_path = tmp_path / "test_cortex.db"
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


class TestContinuityEvent:
    """Test the ContinuityEvent dataclass."""

    def test_create_event(self):
        event = ContinuityEvent(
            timestamp="2026-02-28T04:00:00",
            epoch=1740715200.0,
            event_type="git_commit",
            project="cortex",
            summary="3 new commits",
            importance=4,
        )
        assert event.event_type == "git_commit"
        assert event.importance == 4

    def test_default_importance(self):
        event = ContinuityEvent(
            timestamp="2026-02-28T04:00:00",
            epoch=1740715200.0,
            event_type="file_activity",
        )
        assert event.importance == 1

    def test_all_fields(self):
        event = ContinuityEvent(
            timestamp="2026-02-28T04:00:00",
            epoch=1740715200.0,
            event_type="git_dirty",
            project="cortex",
            summary="main: 2 modified",
            detail=" M file.py\n M other.py",
            importance=2,
        )
        assert event.event_type == "git_dirty"
        assert "modified" in event.summary


class TestContinuityState:
    """Test the ContinuityState persistence."""

    def test_default_state(self):
        state = ContinuityState()
        assert state.last_git_hashes == {}
        assert state.last_fact_count == 0
        assert state.last_fact_id == 0
        assert state.last_check_epoch == 0.0
        assert state.active_processes == []
        assert state.last_ghost_set == []

    def test_ghost_set_preserved(self):
        state = ContinuityState(
            last_ghost_set=["cortex", "notchlive"]
        )
        assert len(state.last_ghost_set) == 2


class TestContinuityMonitor:
    """Test the ContinuityMonitor."""

    def test_first_check_no_gap(self, continuity_dir: Path):
        """First check should not report a gap."""
        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        alerts = monitor.check()
        gap_alerts = [a for a in alerts if a.issue == "continuity_gap"]
        assert len(gap_alerts) == 0

    def test_gap_detection(self, continuity_dir: Path):
        """Simulate daemon being offline for 2 hours."""
        old_epoch = time.time() - 7200
        state = {
            "last_git_hashes": {},
            "last_fact_count": 0,
            "last_fact_id": 0,
            "last_check_epoch": old_epoch,
            "active_processes": [],
            "last_ghost_set": [],
        }
        state_file = continuity_dir / "state.json"
        state_file.write_text(json.dumps(state))

        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        alerts = monitor.check()

        gap_alerts = [a for a in alerts if a.issue == "continuity_gap"]
        assert len(gap_alerts) == 1
        assert "2.0h" in gap_alerts[0].detail

    def test_no_gap_within_threshold(self, continuity_dir: Path):
        """No gap alert if last check was recent."""
        recent_epoch = time.time() - 300
        state = {
            "last_git_hashes": {},
            "last_fact_count": 0,
            "last_fact_id": 0,
            "last_check_epoch": recent_epoch,
            "active_processes": [],
            "last_ghost_set": [],
        }
        state_file = continuity_dir / "state.json"
        state_file.write_text(json.dumps(state))

        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        alerts = monitor.check()
        gap_alerts = [a for a in alerts if a.issue == "continuity_gap"]
        assert len(gap_alerts) == 0

    def test_timeline_append(self, continuity_dir: Path):
        """Events should be appended to the timeline JSONL."""
        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        events = [
            ContinuityEvent(
                timestamp="2026-02-28T04:00:00",
                epoch=time.time(),
                event_type="test_event",
                summary="Test summary",
            ),
        ]
        monitor._append_timeline(events)

        timeline_file = continuity_dir / "timeline.jsonl"
        assert timeline_file.exists()
        lines = timeline_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["event_type"] == "test_event"

    def test_timeline_pruning(self, continuity_dir: Path):
        """Timeline should be pruned when exceeding max entries."""
        import cortex.daemon.monitors.continuity as mod

        original_max = mod.MAX_TIMELINE_ENTRIES
        mod.MAX_TIMELINE_ENTRIES = 5

        try:
            timeline_file = continuity_dir / "timeline.jsonl"
            with open(timeline_file, "w") as f:
                for i in range(10):
                    event = {
                        "timestamp": f"2026-02-28T04:{i:02d}:00",
                        "epoch": time.time() + i,
                        "event_type": "test",
                        "summary": f"Event {i}",
                    }
                    f.write(json.dumps(event) + "\n")

            monitor = ContinuityMonitor(
                db_path=Path("/nonexistent/db"),
                watched_dirs=[],
            )
            monitor._prune_timeline()

            lines = timeline_file.read_text().strip().split("\n")
            assert len(lines) == 5
            last = json.loads(lines[-1])
            assert last["summary"] == "Event 9"
        finally:
            mod.MAX_TIMELINE_ENTRIES = original_max

    def test_briefing_generation(self, continuity_dir: Path):
        """Briefing should be generated from timeline events."""
        timeline_file = continuity_dir / "timeline.jsonl"
        briefing_file = continuity_dir / "briefing.md"

        events = [
            {
                "timestamp": "2026-02-28T04:00:00",
                "epoch": time.time(),
                "event_type": "git_commit",
                "project": "cortex",
                "summary": "3 new commits: feat: add continuity",
                "detail": "5 files changed",
                "importance": 4,
            },
            {
                "timestamp": "2026-02-28T04:01:00",
                "epoch": time.time(),
                "event_type": "fact_created",
                "project": "cortex",
                "summary": "+5 facts: 2 decision, 3 error",
                "importance": 3,
            },
        ]
        with open(timeline_file, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        monitor._generate_briefing()

        assert briefing_file.exists()
        content = briefing_file.read_text()
        assert "Continuity Briefing" in content
        # v2: should have "Últimas 2h" section
        assert "ltimas 2h" in content

    def test_state_persistence(self, continuity_dir: Path):
        """State should persist and reload correctly."""
        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        monitor._state.last_git_hashes = {"cortex": "abc123"}
        monitor._state.last_fact_count = 42
        monitor._state.last_fact_id = 100
        monitor._state.last_check_epoch = 1740715200.0
        monitor._state.last_ghost_set = ["cortex", "notchlive"]
        monitor._save_state()

        state_file = continuity_dir / "state.json"
        assert state_file.exists()

        loaded = monitor._load_state()
        assert loaded.last_git_hashes == {"cortex": "abc123"}
        assert loaded.last_fact_count == 42
        assert loaded.last_fact_id == 100
        assert loaded.last_ghost_set == ["cortex", "notchlive"]

    def test_get_briefing_missing(self, continuity_dir: Path):
        """get_briefing() with no file returns helpful message."""
        text = ContinuityMonitor.get_briefing()
        assert "No briefing available" in text

    def test_get_timeline_empty(self, continuity_dir: Path):
        """get_timeline() with no file returns empty list."""
        events = ContinuityMonitor.get_timeline()
        assert events == []

    def test_process_detection(self, continuity_dir: Path):
        """Process scanner should detect state changes."""
        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        monitor._state.active_processes = ["Vite dev server"]

        now = datetime.now(timezone.utc)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "USER PID COMMAND\n"
            mock_run.return_value.returncode = 0
            events = monitor._scan_processes(now)

        stopped = [e for e in events if e.event_type == "process_stopped"]
        assert len(stopped) == 1
        assert "Vite dev server" in stopped[0].summary

    # ─── v2 Tests ──────────────────────────────────────────────────

    def test_fact_scan_uses_correct_column(
        self, continuity_dir: Path, fake_db: Path
    ):
        """Verify fact scan queries fact_type, not type."""
        conn = sqlite3.connect(str(fake_db))
        for i in range(3):
            conn.execute(
                "INSERT INTO facts (project, content, fact_type, valid_from) "
                "VALUES (?, ?, ?, datetime('now'))",
                ("cortex", f"Decision {i}", "decision"),
            )
        conn.commit()
        conn.close()

        monitor = ContinuityMonitor(
            db_path=fake_db, watched_dirs=[]
        )
        # Set baseline
        monitor._state.last_fact_count = 1
        now = datetime.now(timezone.utc)
        events = monitor._scan_cortex_facts(now)

        assert len(events) == 1
        assert "decision" in events[0].summary
        assert "Decision" in events[0].detail

    def test_git_dirty_detection(self, continuity_dir: Path):
        """Git dirty scanner should detect uncommitted changes."""
        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        now = datetime.now(timezone.utc)

        with patch("subprocess.run") as mock_run:
            # First call: branch name
            branch_result = type("R", (), {
                "stdout": "main\n", "returncode": 0
            })()
            # Second call: status
            status_result = type("R", (), {
                "stdout": " M file.py\n M other.py\n?? new.py\n",
                "returncode": 0,
            })()
            mock_run.side_effect = [branch_result, status_result]

            ev = monitor._check_dirty(Path("/fake/repo"), now)

        assert ev is not None
        assert ev.event_type == "git_dirty"
        assert "main" in ev.summary
        assert "modified" in ev.summary
        assert "untracked" in ev.summary

    def test_ghost_evolution_tracking(
        self, continuity_dir: Path, tmp_path: Path
    ):
        """Ghost scanner should detect creation and resolution."""
        ghosts_file = tmp_path / "ghosts.json"

        # Start with 1 ghost
        ghosts_file.write_text(json.dumps({"cortex": {}}))
        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
            ghosts_path=ghosts_file,
        )
        # Set previous state: no ghosts known
        monitor._state.last_ghost_set = []
        now = datetime.now(timezone.utc)

        events = monitor._scan_ghost_evolution(now)
        created = [e for e in events if e.event_type == "ghost_created"]
        assert len(created) == 1
        assert "cortex" in created[0].summary

        # Now resolve it
        ghosts_file.write_text(json.dumps({}))
        monitor._state.last_ghost_set = ["cortex"]
        events = monitor._scan_ghost_evolution(now)
        resolved = [e for e in events if e.event_type == "ghost_resolved"]
        assert len(resolved) == 1
        assert "cortex" in resolved[0].summary

    def test_temporal_bucketing(self, continuity_dir: Path):
        """Briefing should include temporal bucketing section."""
        timeline_file = continuity_dir / "timeline.jsonl"
        briefing_file = continuity_dir / "briefing.md"

        # Write events spread across different hours
        now_epoch = time.time()
        events = []
        for i in range(10):
            events.append({
                "timestamp": f"2026-02-28T{i % 24:02d}:00:00",
                "epoch": now_epoch - (i * 60),  # within 2h window
                "event_type": "file_activity",
                "summary": f"Files modified batch {i}",
                "importance": 1,
            })

        with open(timeline_file, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        monitor._generate_briefing()

        content = briefing_file.read_text()
        assert "Actividad por Periodo" in content

    def test_decision_extraction(
        self, continuity_dir: Path, fake_db: Path
    ):
        """Briefing should include recent decisions from DB."""
        conn = sqlite3.connect(str(fake_db))
        conn.execute(
            "INSERT INTO facts (project, content, fact_type, valid_from) "
            "VALUES (?, ?, ?, datetime('now'))",
            ("cortex", "Implement ContinuityMonitor v2", "decision"),
        )
        conn.commit()
        conn.close()

        monitor = ContinuityMonitor(
            db_path=fake_db, watched_dirs=[]
        )

        lines = monitor._section_decisions()
        text = "\n".join(lines)
        assert "Decisiones Recientes" in text
        assert "ContinuityMonitor" in text

    def test_decay_compression(self, continuity_dir: Path):
        """Briefing should have 3 decay tiers: detail, summary, counts."""
        timeline_file = continuity_dir / "timeline.jsonl"
        briefing_file = continuity_dir / "briefing.md"

        now_epoch = time.time()
        events = []
        # Tier 1: within 2h (detail)
        for i in range(3):
            events.append({
                "timestamp": "2026-02-28T04:00:00",
                "epoch": now_epoch - (i * 300),
                "event_type": "git_commit",
                "project": "cortex",
                "summary": f"Commit tier1-{i}",
                "importance": 3,
            })
        # Tier 2: 2-4h ago (summary)
        for i in range(3):
            events.append({
                "timestamp": "2026-02-28T02:00:00",
                "epoch": now_epoch - 10800 - (i * 300),
                "event_type": "git_commit",
                "project": "cortex",
                "summary": f"Commit tier2-{i}",
                "importance": 3,
            })
        # Tier 3: 4-8h ago (counts)
        for i in range(3):
            events.append({
                "timestamp": "2026-02-28T00:00:00",
                "epoch": now_epoch - 21600 - (i * 300),
                "event_type": "file_activity",
                "summary": f"Files tier3-{i}",
                "importance": 1,
            })

        with open(timeline_file, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        monitor = ContinuityMonitor(
            db_path=Path("/nonexistent/db"),
            watched_dirs=[],
        )
        monitor._generate_briefing()

        content = briefing_file.read_text()
        assert "ltimas 2h" in content  # Tier 1 (Últimas 2h)
        assert "Hace 2-4h" in content  # Tier 2
        assert "Hace 4-8h" in content  # Tier 3
