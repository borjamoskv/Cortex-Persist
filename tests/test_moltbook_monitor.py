"""Tests for MoltbookMonitor daemon integration."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch


from cortex.daemon.models import MoltbookAlert
from cortex.daemon.monitors.moltbook import MoltbookMonitor


class TestMoltbookMonitor:
    """Test the MoltbookMonitor daemon integration."""

    def test_skips_when_interval_not_elapsed(self):
        monitor = MoltbookMonitor(interval_seconds=3600)
        monitor._last_run = time.monotonic()  # Just ran
        assert monitor.check() == []

    @patch("cortex.moltbook.heartbeat.MoltbookHeartbeat")
    def test_runs_heartbeat_on_first_check(self, mock_hb_cls):
        mock_hb = MagicMock()
        mock_hb.run.return_value = {
            "actions": ["checked_home", "upvoted_5_posts"],
            "errors": [],
            "home": {"karma": 42},
        }
        mock_hb_cls.return_value = mock_hb

        monitor = MoltbookMonitor(interval_seconds=60)
        alerts = monitor.check()

        assert len(alerts) == 1
        assert alerts[0].success is True
        assert alerts[0].karma == 42
        assert "checked_home" in alerts[0].actions_taken
        assert "upvoted_5_posts" in alerts[0].actions_taken
        mock_hb.run.assert_called_once()

    @patch("cortex.moltbook.heartbeat.MoltbookHeartbeat")
    def test_reports_errors_from_heartbeat(self, mock_hb_cls):
        mock_hb = MagicMock()
        mock_hb.run.return_value = {
            "actions": ["checked_home"],
            "errors": ["rate_limited_retry_after_60s"],
            "home": {"karma": 7},
        }
        mock_hb_cls.return_value = mock_hb

        monitor = MoltbookMonitor(interval_seconds=0)
        alerts = monitor.check()

        assert len(alerts) == 1
        assert alerts[0].success is False
        assert "rate_limited" in alerts[0].message

    @patch("cortex.moltbook.heartbeat.MoltbookHeartbeat")
    def test_handles_import_error(self, mock_hb_cls):
        mock_hb_cls.side_effect = ImportError("moltbook not installed")

        monitor = MoltbookMonitor(interval_seconds=0)
        alerts = monitor.check()

        assert len(alerts) == 1
        assert alerts[0].success is False
        assert "Monitor error" in alerts[0].message

    @patch("cortex.moltbook.heartbeat.MoltbookHeartbeat")
    def test_respects_interval(self, mock_hb_cls):
        mock_hb = MagicMock()
        mock_hb.run.return_value = {
            "actions": ["checked_home"],
            "errors": [],
            "home": {"karma": 10},
        }
        mock_hb_cls.return_value = mock_hb

        monitor = MoltbookMonitor(interval_seconds=0)
        # First call should run (interval=0 always passes)
        alerts1 = monitor.check()
        assert len(alerts1) == 1
        assert mock_hb.run.call_count == 1

        # Now set a huge interval — second call should skip
        monitor.interval_seconds = 99999
        alerts2 = monitor.check()
        assert alerts2 == []
        assert mock_hb.run.call_count == 1  # Still only called once

    def test_default_interval_is_4_hours(self):
        monitor = MoltbookMonitor()
        assert monitor.interval_seconds == 14400


class TestMoltbookAlert:
    """Test MoltbookAlert dataclass."""

    def test_creates_alert(self):
        alert = MoltbookAlert(
            karma=42,
            actions_taken=["checked_home", "upvoted_3_posts"],
            message="Heartbeat OK",
            success=True,
        )
        assert alert.karma == 42
        assert len(alert.actions_taken) == 2
        assert alert.success is True

    def test_serializes_in_daemon_status(self):
        from cortex.daemon.models import DaemonStatus

        status = DaemonStatus(
            checked_at="2026-02-28T05:00:00Z",
            moltbook_alerts=[
                MoltbookAlert(
                    karma=7,
                    actions_taken=["checked_home"],
                    message="Heartbeat OK",
                    success=True,
                )
            ],
        )
        d = status.to_dict()
        assert "moltbook_alerts" in d
        assert len(d["moltbook_alerts"]) == 1
        assert d["moltbook_alerts"][0]["karma"] == 7
        assert d["moltbook_alerts"][0]["success"] is True


class TestHeartbeatSkillCheck:
    """Test that heartbeat run() checks skill version."""

    @patch("cortex.moltbook.heartbeat.MoltbookClient")
    def test_heartbeat_updates_skill_version(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get_home.return_value = {
            "your_account": {"karma": 10, "unread_notification_count": 0},
            "activity_on_your_posts": [],
            "your_direct_messages": {},
        }
        mock_client.get_feed.return_value = {"posts": []}
        mock_client.check_skill_version.return_value = "1.13.0"
        mock_client_cls.return_value = mock_client

        from cortex.moltbook.heartbeat import MoltbookHeartbeat

        with patch("cortex.moltbook.heartbeat._STATE_PATH") as mock_path:
            mock_path.exists.return_value = False
            mock_path.parent.mkdir = MagicMock()
            mock_path.write_text = MagicMock()

            hb = MoltbookHeartbeat(client=mock_client)
            hb._store_fact = MagicMock(return_value=1)
            summary = hb.run()

        mock_client.check_skill_version.assert_called_once()
        assert "skill_check_v1.13.0" in summary["actions"]
        assert hb._state["skill_version"] == "1.13.0"
        assert hb._state["last_skill_update_check"] is not None


class TestHeartbeatCortexPersistence:
    """Test that heartbeat persists results to CORTEX via _store_fact."""

    @patch("cortex.moltbook.heartbeat.MoltbookClient")
    def test_heartbeat_persists_to_cortex(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get_home.return_value = {
            "your_account": {"karma": 42, "unread_notification_count": 0},
            "activity_on_your_posts": [],
            "your_direct_messages": {},
        }
        mock_client.get_feed.return_value = {"posts": []}
        mock_client.check_skill_version.return_value = "1.12.0"
        mock_client_cls.return_value = mock_client

        from cortex.moltbook.heartbeat import MoltbookHeartbeat

        with patch("cortex.moltbook.heartbeat._STATE_PATH") as mock_path:
            mock_path.exists.return_value = False
            mock_path.parent.mkdir = MagicMock()
            mock_path.write_text = MagicMock()

            hb = MoltbookHeartbeat(client=mock_client)
            mock_store = MagicMock(return_value=1)
            hb._store_fact = mock_store
            hb.run()

        mock_store.assert_called()
        call_args = mock_store.call_args
        assert "karma=42" in call_args[0][0]


class TestHeartbeatKnowledgeAbsorption:
    """Test the knowledge absorption pipeline."""

    def test_absorb_filters_bots(self):
        from cortex.moltbook.heartbeat import MoltbookHeartbeat

        with patch("cortex.moltbook.heartbeat._STATE_PATH") as mock_path:
            mock_path.exists.return_value = False
            hb = MoltbookHeartbeat(client=MagicMock())
            hb._store_fact = MagicMock(return_value=1)

            posts = [
                {
                    "id": "1",
                    "author": {"name": "crabkarmabot"},
                    "title": "Memory test",
                    "content": "x" * 200,
                    "upvotes": 100,
                },
            ]
            absorbed = hb._absorb_knowledge(posts)
            assert absorbed == 0

    def test_absorb_filters_short_content(self):
        from cortex.moltbook.heartbeat import MoltbookHeartbeat

        with patch("cortex.moltbook.heartbeat._STATE_PATH") as mock_path:
            mock_path.exists.return_value = False
            hb = MoltbookHeartbeat(client=MagicMock())
            hb._store_fact = MagicMock(return_value=1)

            posts = [
                {
                    "id": "2",
                    "author": {"name": "real_agent"},
                    "title": "Nice",
                    "content": "Short",
                    "upvotes": 100,
                },
            ]
            absorbed = hb._absorb_knowledge(posts)
            assert absorbed == 0

    def test_absorb_relevant_post(self):
        from cortex.moltbook.heartbeat import MoltbookHeartbeat

        with patch("cortex.moltbook.heartbeat._STATE_PATH") as mock_path:
            mock_path.exists.return_value = False
            hb = MoltbookHeartbeat(client=MagicMock())
            hb._store_fact = MagicMock(return_value=1)

            posts = [
                {
                    "id": "3",
                    "author": {"name": "real_agent"},
                    "title": "Agent memory architecture for persistent context",
                    "content": "The agent memory system needs persistent "
                    "context recall with security and integrity. " * 5,
                    "upvotes": 500,
                },
            ]
            absorbed = hb._absorb_knowledge(posts)
            assert absorbed == 1
            hb._store_fact.assert_called_once()

    def test_absorb_respects_quota(self):
        from cortex.moltbook.heartbeat import MoltbookHeartbeat

        with patch("cortex.moltbook.heartbeat._STATE_PATH") as mock_path:
            mock_path.exists.return_value = False
            hb = MoltbookHeartbeat(client=MagicMock())
            hb._store_fact = MagicMock(return_value=1)

            posts = [
                {
                    "id": str(i),
                    "author": {"name": f"agent_{i}"},
                    "title": "Agent memory architecture persistent context",
                    "content": "Memory agent persistent context security. " * 10,
                    "upvotes": 500,
                }
                for i in range(10)
            ]
            absorbed = hb._absorb_knowledge(posts)
            assert absorbed == 5  # Max quota

    def test_absorb_dedup(self):
        from cortex.moltbook.heartbeat import MoltbookHeartbeat

        with patch("cortex.moltbook.heartbeat._STATE_PATH") as mock_path:
            mock_path.exists.return_value = False
            hb = MoltbookHeartbeat(client=MagicMock())
            hb._store_fact = MagicMock(return_value=1)
            hb._state["absorbed_post_ids"] = ["existing-id"]

            posts = [
                {
                    "id": "existing-id",
                    "author": {"name": "real_agent"},
                    "title": "Agent memory architecture persistent context",
                    "content": "Memory agent persistent context security. " * 10,
                    "upvotes": 500,
                },
            ]
            absorbed = hb._absorb_knowledge(posts)
            assert absorbed == 0
