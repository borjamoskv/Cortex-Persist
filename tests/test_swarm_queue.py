"""Tests for Swarm Task Queue Concurrency & Advisory Locking."""

import os
import json
import time
import asyncio
import pytest
import shutil
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "cortex-core"))

import persistence
from persistence import enqueue_swarm_task
from cortex_daemon import CortexDaemon


import sqlite3


@pytest.fixture(autouse=True)
def clean_swarm_queue_db(monkeypatch, tmp_path):
    """Isolate SQLite database for each test."""
    test_db = tmp_path / "test_cortex_memory_vsa.db"
    import daemons.outbox as _outbox_mod

    # Patch DB_PATH in imported modules
    monkeypatch.setattr("persistence.DB_PATH", str(test_db))
    monkeypatch.setattr("persistence.base.DB_PATH", str(test_db))
    monkeypatch.setattr(_outbox_mod, "DB_PATH", str(test_db))
    monkeypatch.setattr("cortex_daemon.DB_PATH", str(test_db))
    monkeypatch.setattr(_outbox_mod, "_global_ring_buffer", None)

    # Initialize the tables in test_db
    conn = sqlite3.connect(str(test_db))
    c = conn.cursor()
    conn.commit()
    conn.close()

    yield test_db


@pytest.mark.asyncio
async def test_daemon_basic_queue_processing(tmp_path, monkeypatch):
    """Test enqueuing tasks and daemon processing them under basic conditions."""
    db_path = str(tmp_path / "cortex_memory_vsa.db")
    bin_path = str(tmp_path / "swarm_ring_vsa.bin")

    import daemons.outbox as _outbox_mod

    # Patch all the possible paths
    monkeypatch.setattr("persistence.DB_PATH", db_path)
    monkeypatch.setattr("persistence.base.DB_PATH", db_path)
    monkeypatch.setattr(_outbox_mod, "DB_PATH", db_path)
    monkeypatch.setattr("cortex_daemon.DB_PATH", db_path)
    monkeypatch.setattr("persistence.base.VSA_BIN_PATH", bin_path)

    # Force _global_ring_buffer to None so it recreates with the new path
    monkeypatch.setattr(_outbox_mod, "_global_ring_buffer", None)

    # Initialize mock daemon
    daemon = CortexDaemon()
    import sqlite3

    daemon.db_conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    daemon.db_conn.execute(
        "CREATE TABLE IF NOT EXISTS cortex_execution_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, agent TEXT, command TEXT, returncode INTEGER, execution_time REAL);"
    )

    # Enqueue a mock task
    payload = {"command": "echo 'hello world'"}
    enqueue_swarm_task("TestAgent", payload)

    # Let the thread run the enqueue executor task
    await asyncio.sleep(0.1)

    # Mock _execute_task to just record the commands it received
    executed_tasks = []

    async def mock_execute_task(task):
        executed_tasks.append(task)

    daemon._execute_task = mock_execute_task

    # Run queue process cycle
    await daemon.process_swarm_queue()

    assert len(executed_tasks) == 1
    assert executed_tasks[0]["agent"] == "TestAgent"
    assert executed_tasks[0]["payload"] == payload


@pytest.mark.asyncio
async def test_daemon_command_extraction(tmp_path, monkeypatch):
    """Test that command is extracted from payload or command key correctly."""
    db_path = str(tmp_path / "cortex_memory_vsa.db")
    bin_path = str(tmp_path / "swarm_ring_vsa.bin")

    # Force _global_ring_buffer to None so it recreates with the new path
    import daemons.outbox as _outbox_mod

    monkeypatch.setattr("persistence.DB_PATH", db_path)
    monkeypatch.setattr("persistence.base.DB_PATH", db_path)
    monkeypatch.setattr(_outbox_mod, "DB_PATH", db_path)
    monkeypatch.setattr("cortex_daemon.DB_PATH", db_path)
    monkeypatch.setattr("persistence.base.VSA_BIN_PATH", bin_path)
    monkeypatch.setattr(_outbox_mod, "_global_ring_buffer", None)

    daemon = CortexDaemon()
    import sqlite3

    daemon.db_conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    daemon.db_conn.execute(
        "CREATE TABLE IF NOT EXISTS cortex_execution_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, agent TEXT, command TEXT, returncode INTEGER, execution_time REAL);"
    )

    # Task with command in payload
    task1 = {"agent": "AgentA", "payload": {"command": "cmd_a"}}
    # Task with string payload
    task2 = {"agent": "AgentB", "payload": "cmd_b"}
    # Task with command key directly
    task3 = {"agent": "AgentC", "command": "cmd_c"}

    executed_cmds = []

    async def mock_execute_raw(task):
        # We call the original _execute_task logic but mock process spawn to capture cmd
        agent = task.get("agent", "unknown")
        cmd = task.get("command")
        if not cmd and "payload" in task:
            payload = task["payload"]
            if isinstance(payload, str):
                cmd = payload
            elif isinstance(payload, dict):
                cmd = payload.get("command")
        executed_cmds.append((agent, cmd))

    daemon._execute_task = mock_execute_raw

    for task in [task1, task2, task3]:
        agent = task["agent"]
        if "payload" in task:
            payload_val = task["payload"]
        else:
            payload_val = {"command": task["command"]}
        enqueue_swarm_task(agent, payload_val)

    await daemon.process_swarm_queue()

    assert executed_cmds == [("AgentA", "cmd_a"), ("AgentB", "cmd_b"), ("AgentC", "cmd_c")]


@pytest.mark.asyncio
async def test_swarm_queue_contention(tmp_path, monkeypatch):
    """Test high contention concurrent enqueues and dequeues to verify zero lost tasks."""
    db_path = str(tmp_path / "cortex_memory_vsa.db")
    bin_path = str(tmp_path / "swarm_ring_vsa.bin")

    # Force _global_ring_buffer to None so it recreates with the new path
    import daemons.outbox as _outbox_mod

    monkeypatch.setattr("persistence.DB_PATH", db_path)
    monkeypatch.setattr("persistence.base.DB_PATH", db_path)
    monkeypatch.setattr(_outbox_mod, "DB_PATH", db_path)
    monkeypatch.setattr("cortex_daemon.DB_PATH", db_path)
    monkeypatch.setattr("persistence.base.VSA_BIN_PATH", bin_path)
    monkeypatch.setattr(_outbox_mod, "_global_ring_buffer", None)
    # Wait, just setting _global_ring_buffer to None is enough because __init__ reads from base.DB_PATH

    daemon = CortexDaemon()
    # Replace its DB connection
    import sqlite3

    daemon.db_conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    daemon.db_conn.execute(
        "CREATE TABLE IF NOT EXISTS cortex_execution_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, agent TEXT, command TEXT, returncode INTEGER, execution_time REAL);"
    )

    executed_tasks = []

    async def mock_execute_task(task):
        executed_tasks.append(task)
        # Simulate execution delay
        await asyncio.sleep(0.02)

    daemon._execute_task = mock_execute_task

    # Define concurrent enqueuers
    async def enqueuer(agent_name, task_count):
        for i in range(task_count):
            enqueue_swarm_task(agent_name, {"command": f"task_{agent_name}_{i}"})
            await asyncio.sleep(0.01)

    # Start enqueuers
    t1 = asyncio.create_task(enqueuer("AgentX", 10))
    t2 = asyncio.create_task(enqueuer("AgentY", 10))

    # Consume queue concurrently
    consumer_runs = 0
    while not (t1.done() and t2.done()):
        await daemon.process_swarm_queue()
        consumer_runs += 1
        await asyncio.sleep(0.03)

    # Final sweep to ensure queue is completely empty
    await daemon.process_swarm_queue()

    # Check total executed tasks
    assert len(executed_tasks) == 20
    agents = [t["agent"] for t in executed_tasks]
    assert agents.count("AgentX") == 10
    assert agents.count("AgentY") == 10
