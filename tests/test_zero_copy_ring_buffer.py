import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

from persistence import ZeroCopyRingBuffer, VSAMemory, DB_PATH, VSA_BIN_PATH


@pytest.fixture(autouse=True)
def clean_vsa_env(monkeypatch, tmp_path):
    """Isolate DB and bin paths to tmp_path to prevent xdist concurrency conflicts."""
    test_db = tmp_path / "test_cortex.db"
    
    monkeypatch.setattr("persistence.DB_PATH", str(test_db))
    monkeypatch.setattr("persistence.VSA_BIN_PATH", str(tmp_path / "vsa.bin"))
    yield



def test_ring_buffer_lifecycle():
    """Test standard queue and dequeue workflow for the ZeroCopyRingBuffer."""
    buffer = ZeroCopyRingBuffer(capacity=10)

    agent_id = b"agent_test_id"
    payload = b"payload_bytes"

    # Verify enqueue
    success = buffer.enqueue(agent_id, payload)
    assert success is True

    # Verify fetch
    pending = buffer.fetch_pending()
    assert len(pending) == 1

    idx, ts, fetched_agent_id, fetched_payload = pending[0]
    assert idx == 0
    assert fetched_agent_id == agent_id
    assert fetched_payload == payload
    assert ts <= time.time()


def test_ring_buffer_overflow():
    """Verify that buffer returns False if capacity is exceeded."""
    buffer = ZeroCopyRingBuffer(capacity=2)

    assert buffer.enqueue(b"a1", b"p1") is True
    assert buffer.enqueue(b"a2", b"p2") is True
    assert buffer.enqueue(b"a3", b"p3") is False  # Full!


def test_vsa_memory_rust_integration():
    """Verify that VSAMemory utilizes Rust substrate delegation if available."""
    import sqlite3

    vsa = VSAMemory()

    # Check if substrate is initialized (assuming HAS_CORTEX_RS is True in this environment)
    from persistence import HAS_CORTEX_RS

    if HAS_CORTEX_RS:
        assert vsa._substrate is not None
    else:
        assert vsa._substrate is None

    # Pre-create the database table if it doesn't exist
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cortex_knowledge (ki_id TEXT PRIMARY KEY, summary TEXT, content TEXT)"
    )
    conn.execute("DELETE FROM cortex_knowledge WHERE summary = 'agent_id_x'")
    conn.commit()
    conn.close()

    # Record semantic trace
    vsa.record("agent_id_x", "payload_y")

    # Read from database to verify persistence
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT summary, content FROM cortex_knowledge WHERE summary = 'agent_id_x'")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][0] == "agent_id_x"
    assert rows[0][1] == "payload_y"
