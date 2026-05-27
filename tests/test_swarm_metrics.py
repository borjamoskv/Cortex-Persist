"""Tests for get_swarm_metrics cache and database query optimizations."""

import time
import pytest
import sqlite3
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "cortex-core"))

import persistence
from persistence import get_swarm_metrics


@pytest.fixture(autouse=True)
def clean_swarm_queue_db(monkeypatch, tmp_path):
    """Isolate SQLite database for each test and reset cache."""
    test_db = tmp_path / "test_cortex_memory_vsa.db"
    import daemons.outbox as _outbox_mod

    # Patch DB_PATH in imported modules
    monkeypatch.setattr("persistence.DB_PATH", str(test_db))
    monkeypatch.setattr("persistence.base.DB_PATH", str(test_db))
    monkeypatch.setattr(_outbox_mod, "DB_PATH", str(test_db))
    monkeypatch.setattr(_outbox_mod, "_global_ring_buffer", None)

    # Reset thread-local connections to avoid test cross-contamination
    from persistence.base import _local

    if hasattr(_local, "conn"):
        try:
            _local.conn.close()
        except Exception:
            pass
        delattr(_local, "conn")
    if hasattr(_local, "db_path"):
        delattr(_local, "db_path")

    # Reset cache
    with persistence._metrics_cache_lock:
        persistence._metrics_cache["value"] = None
        persistence._metrics_cache["expiry"] = 0.0

    # Initialize the tables in test_db
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS cortex_execution_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            agent TEXT,
            command TEXT,
            returncode INTEGER,
            execution_time REAL
        )
    """)
    conn.commit()
    conn.close()

    yield test_db


def test_swarm_metrics_caching():
    """Verify that get_swarm_metrics caches responses and respects bypass_cache."""
    # First call - cache miss
    m1 = get_swarm_metrics()
    assert m1["latency_ms"] == 35.0
    assert m1["active_children"] == 0
    assert m1["uncertainty"] == 0.0

    # Second call - cache hit (returns the exact same dictionary object)
    m2 = get_swarm_metrics()
    assert m2 is m1

    # Bypass cache call - executes database query again and returns a new object
    m3 = get_swarm_metrics(bypass_cache=True)
    assert m3 is not m1
    assert m3 == m1

    # Insert a task and verify update works when bypassing or after cache expires
    conn = sqlite3.connect(persistence.DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO cortex_execution_ledger (timestamp, agent, command, returncode, execution_time) VALUES (?, ?, ?, ?, ?)",
        (time.time(), "TestAgent", "TestCmd", 0, 0.5),
    )
    conn.commit()
    conn.close()

    # Cached call should still return old values (latency_ms == 35.0)
    m4 = get_swarm_metrics()
    assert m4 is m3
    assert m4["latency_ms"] == 35.0

    # Bypassed call should return updated value (latency_ms == 500.0)
    m5 = get_swarm_metrics(bypass_cache=True)
    assert m5["latency_ms"] == 500.0
    assert m5 is not m1

    # Let the cache expire (500ms)
    time.sleep(0.6)

    # Next call should be a cache miss, returning updated values
    m6 = get_swarm_metrics()
    assert m6["latency_ms"] == 500.0
    assert m6 is not m1


def test_swarm_metrics_active_children():
    """Verify that active_children counts pending tasks from both SQLite and ZeroCopyRingBuffer."""
    # Initially 0
    m = get_swarm_metrics(bypass_cache=True)
    assert m["active_children"] == 0

    # 1. Insert into SQLite cortex_swarm_queue
    conn = sqlite3.connect(persistence.DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO cortex_swarm_queue (timestamp, agent, payload, status) VALUES (?, ?, ?, ?)",
        (time.monotonic(), "TestAgent", "{}", "pending"),
    )
    conn.commit()
    conn.close()

    m = get_swarm_metrics(bypass_cache=True)
    assert m["active_children"] == 1

    # 2. Enqueue into ZeroCopyRingBuffer
    ring = persistence._get_ring_buffer()
    # Write a pending task (status = 1)
    success = ring.enqueue(b"TestAgentRing", b"{}")
    assert success is True

    # Total should be 2 (1 from SQLite + 1 from Ring Buffer)
    m = get_swarm_metrics(bypass_cache=True)
    assert m["active_children"] == 2
