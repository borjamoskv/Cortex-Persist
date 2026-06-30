# [C5-REAL] Exergy-Maximized
"""
Tests for Causal FSM Observability endpoints.
Verifies that the /observability/fsm/stream SSE endpoint is active and works correctly.
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from babylon60.api.core import app


@pytest.fixture
def temp_aof(tmp_path):
    """Create a temporary AOF ledger file with dummy state mutations."""
    aof_file = tmp_path / "test_cortex_state.aof"
    mutations = [
        {"hash_id": "tx_001", "action_type": "MUTATE", "payload": {"key": "val1"}},
        {"hash_id": "tx_002", "action_type": "COMMIT", "payload": {"key": "val2"}},
    ]
    with open(aof_file, "w", encoding="utf-8") as f:
        for m in mutations:
            f.write(json.dumps(m) + "\n")
    return aof_file


def test_observability_fsm_stream_endpoint_exists():
    """Verify that the /observability/fsm/stream route is successfully registered."""
    client = TestClient(app)

    async def mock_watcher(*args, **kwargs):
        yield {"event": "state_mutation", "id": "tx_mock", "data": "{}"}

    with patch("babylon60.api.fsm_streamer.ledger_byte_watcher", side_effect=mock_watcher):
        with client.stream("GET", "/observability/fsm/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_ledger_byte_watcher_emits_mutations(temp_aof):
    """Test that ledger_byte_watcher correctly reads and yields AOF deltas from the ledger."""
    from babylon60.api.fsm_streamer import ledger_byte_watcher

    # Mock the Request disconnect check and AOF path
    class MockRequest:
        async def is_disconnected(self):
            return False

    mock_request = MockRequest()

    with patch("babylon60.api.fsm_streamer.get_ledger_path", return_value=str(temp_aof)):
        # Run watcher loop once (using a shorter poll interval or breaking manually)
        watcher_generator = ledger_byte_watcher(mock_request, poll_interval=0.1)

        # Retrieve first event
        event1 = await anext(watcher_generator)
        assert event1["event"] == "state_mutation"
        assert event1["id"] == "tx_001"
        data1 = json.loads(event1["data"])
        assert data1["action_type"] == "MUTATE"

        # Retrieve second event
        event2 = await anext(watcher_generator)
        assert event2["event"] == "state_mutation"
        assert event2["id"] == "tx_002"
        data2 = json.loads(event2["data"])
        assert data2["action_type"] == "COMMIT"
