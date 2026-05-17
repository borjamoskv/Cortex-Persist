import asyncio
import pytest
from cortex.extensions.notifications.bus import (
    NotificationBus,
    get_notification_bus,
    reset_notification_bus,
)
from cortex.extensions.notifications.events import CortexEvent, EventSeverity
from cortex.extensions.notifications.adapters.base import BaseAdapter
from cortex.extensions.notifications.adapters.webhook import WebhookAdapter


class MockAdapter(BaseAdapter):
    def __init__(self, name: str, is_configured: bool = True, throw_on_send: bool = False):
        self._name = name
        self._is_configured = is_configured
        self.throw_on_send = throw_on_send
        self.sent_events = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_configured(self) -> bool:
        return self._is_configured

    async def send(self, event: CortexEvent) -> None:
        if self.throw_on_send:
            raise ValueError(f"Simulated failure in {self.name}")
        self.sent_events.append(event)


@pytest.fixture(autouse=True)
def reset_bus_singleton():
    reset_notification_bus()
    yield
    reset_notification_bus()


@pytest.mark.asyncio
async def test_register_configured_adapter():
    bus = NotificationBus()
    adapter = MockAdapter("test-adapter", is_configured=True)
    bus.register(adapter)

    assert bus.adapter_names == ["test-adapter"]


@pytest.mark.asyncio
async def test_register_unconfigured_adapter():
    bus = NotificationBus()
    adapter = MockAdapter("test-adapter", is_configured=False)
    bus.register(adapter)

    assert bus.adapter_names == []


@pytest.mark.asyncio
async def test_emit_filters_by_severity():
    bus = NotificationBus()

    debug_adapter = MockAdapter("debug-adapter")
    warn_adapter = MockAdapter("warn-adapter")

    bus.register(debug_adapter, min_severity=EventSeverity.DEBUG)
    bus.register(warn_adapter, min_severity=EventSeverity.WARNING)

    # Emit INFO event
    info_event = CortexEvent(
        severity=EventSeverity.INFO, title="Info event", body="This is an info event", source="test"
    )
    await bus.emit(info_event)

    assert len(debug_adapter.sent_events) == 1
    assert len(warn_adapter.sent_events) == 0

    # Emit ERROR event
    error_event = CortexEvent(
        severity=EventSeverity.ERROR,
        title="Error event",
        body="This is an error event",
        source="test",
    )
    await bus.emit(error_event)

    assert len(debug_adapter.sent_events) == 2
    assert len(warn_adapter.sent_events) == 1


@pytest.mark.asyncio
async def test_emit_ignores_exceptions():
    bus = NotificationBus()

    good_adapter = MockAdapter("good-adapter")
    bad_adapter = MockAdapter("bad-adapter", throw_on_send=True)

    bus.register(good_adapter)
    bus.register(bad_adapter)

    event = CortexEvent(
        severity=EventSeverity.INFO, title="Test event", body="Test body", source="test"
    )

    # Should not raise exception
    await bus.emit(event)

    assert len(good_adapter.sent_events) == 1
    assert len(bad_adapter.sent_events) == 0


def test_singleton_behavior():
    bus1 = get_notification_bus()
    bus2 = get_notification_bus()

    assert bus1 is bus2


@pytest.mark.asyncio
async def test_webhook_adapter_configured():
    adapter = WebhookAdapter(webhook_url="http://test-webhook")
    assert adapter.is_configured is True

    adapter_empty = WebhookAdapter(webhook_url="")
    assert adapter_empty.is_configured is False


@pytest.mark.asyncio
async def test_webhook_adapter_send():
    from unittest.mock import patch, AsyncMock

    url = "http://test-webhook"

    adapter = WebhookAdapter(webhook_url=url)
    event = CortexEvent(
        severity=EventSeverity.ERROR,
        title="Webhook event",
        body="Webhook body",
        source="test",
        project="cortex",
        tags={"critical": "true"},
    )

    with patch(
        "cortex.extensions.notifications.adapters.webhook.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await adapter.send(event)

        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == url
        payload = kwargs["json"]
        assert payload["title"] == "Webhook event"
        assert payload["severity"] == "error"
        assert payload["project"] == "cortex"
        assert payload["tags"]["critical"] == "true"
