import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

from persistence import ZeroCopyRingBuffer, VSAMemory, DB_PATH, VSA_BIN_PATH


@pytest.fixture(autouse=True)
def cleanup_bin_files():
    """Ensure binary files are clean before and after each test."""
    bin_path = os.path.join(os.path.dirname(DB_PATH), "swarm_ring_vsa.bin")
    for path in [bin_path, VSA_BIN_PATH]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    yield
    for path in [bin_path, VSA_BIN_PATH]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


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
