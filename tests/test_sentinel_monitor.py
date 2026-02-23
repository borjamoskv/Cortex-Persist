"""Tests for the Sentinel Monitor Oracle sidecar."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.daemon.sidecar.sentinel_monitor.monitor import TARGET_ADDRESS, SentinelMonitor


@pytest.mark.asyncio
async def test_sentinel_monitor_detects_movement():
    """Verify SentinelMonitor detects outbound movements and triggers alerts."""
    monitor = SentinelMonitor(check_interval=1)

    # Mock OS notification and fact logging
    monitor._notify_os = AsyncMock()
    monitor._log_fact = (
        AsyncMock()
    )  # Note: _log_fact is sync, but we patch it as AsyncMock or MagicMock

    # Actually _log_fact was changed to sync, so let's mock it properly
    monitor._log_fact = MagicMock()

    # Create fake Etherscan API response
    fake_txlist_response = {
        "status": "1",
        "message": "OK",
        "result": [
            {
                "blockNumber": "15000000",
                "timeStamp": "1650000000",
                "hash": "0xabcdef1234567890",
                "from": TARGET_ADDRESS.lower(),
                "to": "0x1234567890abcdef",
                "value": "1000000000000000000",  # 1 ETH
                "isError": "0",
            }
        ],
    }

    # Create fake tokentx response (empty for this test)
    fake_tokentx_response = {"status": "1", "message": "OK", "result": []}

    # Mock the ClientSession.get context manager
    class MockResponse:
        def __init__(self, json_data, status=200):
            self.json_data = json_data
            self.status = status

        async def json(self):
            return self.json_data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_get(url, params=None, **kwargs):
        if params and params.get("action") == "txlist":
            return MockResponse(fake_txlist_response)
        elif params and params.get("action") == "tokentx":
            return MockResponse(fake_tokentx_response)
        return MockResponse({"status": "0", "result": []})

    session_mock = MagicMock()
    session_mock.get.side_effect = mock_get

    # Run the check
    await monitor._check_movements(session_mock)

    # Assertions
    assert monitor.last_block_scanned == 15000000
    monitor._notify_os.assert_called_once()
    assert "1.0000 ETH" in monitor._notify_os.call_args[0][1]

    monitor._log_fact.assert_called_once()
    assert monitor._log_fact.call_args[0][0] == "0xabcdef1234567890"  # tx_hash
    assert monitor._log_fact.call_args[0][2] == "1.0000"  # value
    assert monitor._log_fact.call_args[0][3] == "ETH"  # asset


@pytest.mark.asyncio
async def test_sentinel_monitor_ignores_inbound():
    """Verify SentinelMonitor ignores inbound transactions to the target address."""
    monitor = SentinelMonitor(check_interval=1)
    monitor._notify_os = AsyncMock()
    monitor._log_fact = MagicMock()

    # Fake transaction TO the target address
    fake_txlist_response = {
        "status": "1",
        "result": [
            {
                "blockNumber": "15000001",
                "from": "0x1234567890abcdef",
                "to": TARGET_ADDRESS.lower(),
                "value": "1000000000000000000",
            }
        ],
    }

    def mock_get(url, params=None, **kwargs):
        if params and params.get("action") == "txlist":
            return MockResponse(fake_txlist_response)
        return MockResponse({"status": "1", "result": []})

    class MockResponse:
        def __init__(self, json_data, status=200):
            self.json_data = json_data
            self.status = status

        async def json(self):
            return self.json_data

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    session_mock = MagicMock()
    session_mock.get.side_effect = mock_get

    await monitor._check_movements(session_mock)

    # Assertions
    assert monitor.last_block_scanned == 15000001
    monitor._notify_os.assert_not_called()
    monitor._log_fact.assert_not_called()
