import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from babylon60.extensions.browser.peerd_bridge import PeerdBridgeDaemon


@pytest.mark.asyncio
async def test_peerd_bridge_daemon_handler():
    engine = MagicMock()
    event_bus = AsyncMock()
    daemon = PeerdBridgeDaemon(engine=engine, event_bus=event_bus)

    class MockWebsocket:
        def __init__(self):
            self.messages = [
                json.dumps({"action": "dom_extracted", "payload": {"html": "<div>test</div>"}})
            ]

        async def __aiter__(self):
            for msg in self.messages:
                yield msg

    mock_websocket = MockWebsocket()

    await daemon._handler(mock_websocket)

    # Verify the event bus was called with the correct event and data
    event_bus.publish.assert_called_once_with(
        "browser.task.response", {"action": "dom_extracted", "payload": {"html": "<div>test</div>"}}
    )


@pytest.mark.asyncio
async def test_peerd_bridge_start_stop():
    engine = MagicMock()
    event_bus = AsyncMock()
    daemon = PeerdBridgeDaemon(engine=engine, event_bus=event_bus)

    # Stop immediately to avoid blocking
    daemon._shutdown_event.set()
    await daemon.start()

    assert daemon._shutdown_event.is_set()
