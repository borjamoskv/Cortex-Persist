"""Tests for cortex-core/cortex_daemon.py - Sovereign Orchestrator.

C5-REAL coverage for daemon execution, queue processing, and task hygiene.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

import cortex_daemon

print("IMPORTED CORTEX_DAEMON FROM:", cortex_daemon.__file__)
try:
    print("HAS THREADING:", cortex_daemon.threading)
except AttributeError as e:
    print("ERROR THREADING:", e)


import sqlite3


class TestCortexDaemon:
    @pytest.fixture
    def daemon(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_cortex_memory_vsa.db"
        monkeypatch.setattr(cortex_daemon, "DB_PATH", str(test_db))
        import persistence
        import daemons.outbox as _outbox_mod

        monkeypatch.setattr(persistence, "DB_PATH", str(test_db))
        monkeypatch.setattr(persistence.base, "DB_PATH", str(test_db))
        monkeypatch.setattr(_outbox_mod, "DB_PATH", str(test_db))
        monkeypatch.setattr(_outbox_mod, "_global_ring_buffer", None)

        original_init = _outbox_mod.ZeroCopyRingBuffer.__init__

        def mocked_init(self, capacity=100):
            original_init(self, capacity=capacity)

        monkeypatch.setattr(_outbox_mod.ZeroCopyRingBuffer, "__init__", mocked_init)

        # Reset thread-local connections to avoid cross-contamination
        from persistence.base import _local

        if hasattr(_local, "conn"):
            try:
                _local.conn.close()
            except Exception:
                import logging
                logging.getLogger(__name__).error('DETECTIVE-OMEGA: Silent exception swallowed in test_cortex_daemon.py')
            delattr(_local, "conn")
        if hasattr(_local, "db_path"):
            delattr(_local, "db_path")

        # Initialize the test SQLite schema
        conn = sqlite3.connect(str(test_db))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS cortex_swarm_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                agent TEXT,
                payload TEXT,
                status TEXT
            )
        """)
        conn.commit()
        conn.close()

        d = cortex_daemon.CortexDaemon()

        # Patch paths to use temp dir
        d.bus = MagicMock()
        cortex_daemon.PROJECT_ROOT = tmp_path

        # Create schema for tests
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS cortex_knowledge (id INTEGER PRIMARY KEY, content TEXT)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS cortex_swarm_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, agent TEXT, payload TEXT, status TEXT)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS cortex_execution_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, agent TEXT, command TEXT, returncode INTEGER, execution_time REAL)"
        )
        conn.commit()
        conn.close()

        # Create scratch dir
        (tmp_path / ".scratch").mkdir()

        return d

    def test_ensure_hygiene(self, daemon, tmp_path):
        # Create a large temp file
        scratch_dir = tmp_path / ".scratch"
        large_file = scratch_dir / "test.tmp"
        small_file = scratch_dir / "test2.tmp"

        # Fake sizes with mock since creating a 5MB file is slow
        with patch("os.path.getsize") as mock_getsize, patch("os.remove") as mock_remove:
            # First file is large, second is small
            mock_getsize.side_effect = lambda f: 6000000 if "test.tmp" in f else 1000

            # Create dummy files
            large_file.write_text("dummy")
            small_file.write_text("dummy")

            daemon.ensure_hygiene()

            # Assert only the large file was removed
            mock_remove.assert_called_once()
            assert "test.tmp" in mock_remove.call_args[0][0]

    def test_queue_task(self, daemon):
        import time
        import persistence

        ring = persistence._get_ring_buffer()
        pending_before = len(ring.fetch_pending())

        daemon._queue_task("TEST_AGENT", "echo 'hello'")
        time.sleep(0.1)

        pending = ring.fetch_pending()

        if pending:
            # Assert exactly one new entry was added
            assert len(pending) == pending_before + 1
            # Find our specific entry
            matching = [e for e in pending if b"TEST_AGENT" in e[2]]
            assert len(matching) == 1
            idx, ts, agent_bytes, payload_bytes = matching[0]
            agent = agent_bytes.decode("utf-8", "ignore").rstrip("\x00")
            payload_str = payload_bytes.decode("utf-8", "ignore").rstrip("\x00")
            assert agent == "TEST_AGENT"
            payload = json.loads(payload_str)
            assert payload["command"] == "echo 'hello'"
        else:
            conn = sqlite3.connect(cortex_daemon.DB_PATH)
            c = conn.cursor()
            c.execute("SELECT agent, payload, status FROM cortex_swarm_queue")
            rows = c.fetchall()
            conn.close()

            assert len(rows) == 1
            agent, payload_str, status = rows[0]
            assert agent == "TEST_AGENT"
            payload = json.loads(payload_str)
            assert payload["command"] == "echo 'hello'"
            assert status == "pending"

    @pytest.mark.asyncio
    async def test_execute_task(self, daemon):
        task = {"agent": "TEST", "command": "echo 'success'"}

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"success", b"")
            mock_exec.return_value = mock_proc

            await daemon._execute_task(task)

            mock_exec.assert_called_once_with(
                "echo", "success", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Check if ledger was updated in SQLite
            conn = sqlite3.connect(cortex_daemon.DB_PATH)
            c = conn.cursor()
            c.execute("SELECT agent, command, returncode FROM cortex_execution_ledger")
            ledger = c.fetchall()
            conn.close()

            print("LEDGER ENTRIES:", ledger)

            assert len(ledger) == 1
            assert ledger[0][0] == "TEST"
            assert ledger[0][1] == "echo 'success'"
            assert ledger[0][2] == 0

    @pytest.mark.asyncio
    async def test_process_swarm_queue(self, daemon):
        # Add a task to queue
        daemon._queue_task("AGENT_1", "echo 1")

        with patch.object(daemon, "_execute_task", new_callable=AsyncMock) as mock_execute:
            await daemon.process_swarm_queue()

            # Check if it was executed
            mock_execute.assert_called_once()
            assert mock_execute.call_args[0][0]["agent"] == "AGENT_1"

            # Check if queue status is updated to processing (SQLite) or consumed (Ring Buffer)
            conn = sqlite3.connect(cortex_daemon.DB_PATH)
            c = conn.cursor()
            c.execute("SELECT status FROM cortex_swarm_queue")
            rows = c.fetchall()
            conn.close()

            if rows:
                assert len(rows) == 1
                assert rows[0][0] == "processing"
            else:
                import persistence

                ring = persistence._get_ring_buffer()
                assert len(ring.fetch_pending()) == 0

    @pytest.mark.asyncio
    async def test_run_council_deliberation(self, daemon):
        daemon.cycle_count = 0
        with patch.object(daemon, "_queue_task") as mock_queue:
            await daemon._run_council_deliberation()

            # Check if queued
            mock_queue.assert_called_once()
            assert mock_queue.call_args[0][0] == "SAGE_COUNCIL"
            assert "ouroboros_engine.py" in mock_queue.call_args[0][1]
            assert "LayerZero" in mock_queue.call_args[0][1]
