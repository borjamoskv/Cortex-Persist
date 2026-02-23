"""CORTEX — Notification tests (HYDRA swarm — Test Engineer agent)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from cortex.notifications.adapters.base import BaseAdapter
from cortex.notifications.bus import NotificationBus, reset_notification_bus
from cortex.notifications.events import CortexEvent, EventSeverity

# ─── Fixtures ────────────────────────────────────────────────────────


class MockAdapter(BaseAdapter):
    name = "mock"

    def __init__(self, configured: bool = True) -> None:
        self._configured = configured
        self.received: list[CortexEvent] = []

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def send(self, event: CortexEvent) -> None:
        self.received.append(event)


def make_event(
    severity: EventSeverity = EventSeverity.INFO,
    title: str = "Test Event",
    body: str = "Test body",
    source: str = "test",
    project: str = "cortex",
) -> CortexEvent:
    return CortexEvent(
        severity=severity,
        title=title,
        body=body,
        source=source,
        project=project,
    )


@pytest.fixture(autouse=True)
def reset_bus():
    """Isolate singleton between tests."""
    reset_notification_bus()
    yield
    reset_notification_bus()


# ─── CortexEvent tests ───────────────────────────────────────────────


class TestCortexEvent:
    def test_format_text_with_project(self):
        event = make_event(severity=EventSeverity.ERROR, project="naroa-2026")
        text = event.format_text()
        assert "🔴" in text
        assert "[naroa-2026]" in text
        assert "Test Event" in text

    def test_format_text_without_project(self):
        event = make_event(project="")
        text = event.format_text()
        assert "[]" not in text

    def test_severity_emoji(self):
        assert EventSeverity.CRITICAL.emoji == "💀"
        assert EventSeverity.WARNING.emoji == "⚠️"
        assert EventSeverity.INFO.emoji == "ℹ️"


# ─── NotificationBus tests ───────────────────────────────────────────


class TestNotificationBus:
    def test_register_configured_adapter(self):
        bus = NotificationBus()
        adapter = MockAdapter(configured=True)
        bus.register(adapter)
        assert "mock" in bus.adapter_names

    def test_skip_unconfigured_adapter(self):
        bus = NotificationBus()
        adapter = MockAdapter(configured=False)
        bus.register(adapter)
        assert "mock" not in bus.adapter_names

    @pytest.mark.asyncio
    async def test_emit_delivers_to_all_adapters(self):
        bus = NotificationBus()
        a1, a2 = MockAdapter(), MockAdapter()
        bus.register(a1)
        bus.register(a2)
        event = make_event()
        await bus.emit(event)
        assert len(a1.received) == 1
        assert len(a2.received) == 1

    @pytest.mark.asyncio
    async def test_severity_filtering_blocks_low_severity(self):
        bus = NotificationBus()
        adapter = MockAdapter()
        bus.register(adapter, min_severity=EventSeverity.WARNING)
        await bus.emit(make_event(severity=EventSeverity.INFO))
        assert len(adapter.received) == 0

    @pytest.mark.asyncio
    async def test_severity_filtering_passes_high_severity(self):
        bus = NotificationBus()
        adapter = MockAdapter()
        bus.register(adapter, min_severity=EventSeverity.WARNING)
        await bus.emit(make_event(severity=EventSeverity.ERROR))
        assert len(adapter.received) == 1

    @pytest.mark.asyncio
    async def test_failing_adapter_does_not_crash_bus(self):
        bus = NotificationBus()

        class BrokenAdapter(BaseAdapter):
            name = "broken"

            async def send(self, event: CortexEvent) -> None:
                raise RuntimeError("Simulated adapter failure")

        bus.register(BrokenAdapter())
        good = MockAdapter()
        bus.register(good)

        # Should not raise
        await bus.emit(make_event())
        assert len(good.received) == 1  # good adapter still received it

    @pytest.mark.asyncio
    async def test_emit_no_adapters_is_noop(self):
        bus = NotificationBus()
        # Should not raise even with zero adapters
        await bus.emit(make_event())

    @pytest.mark.asyncio
    async def test_concurrent_emit(self):
        bus = NotificationBus()
        adapter = MockAdapter()
        bus.register(adapter)
        events = [make_event(title=f"Event {i}") for i in range(10)]
        await asyncio.gather(*[bus.emit(e) for e in events])
        assert len(adapter.received) == 10


# ─── TelegramAdapter tests ───────────────────────────────────────────


class TestTelegramAdapter:
    def test_not_configured_without_env(self):
        from cortex.notifications.adapters.telegram import TelegramAdapter

        adapter = TelegramAdapter(token="", chat_id="")
        assert not adapter.is_configured

    def test_configured_with_credentials(self):
        from cortex.notifications.adapters.telegram import TelegramAdapter

        adapter = TelegramAdapter(token="fake_token", chat_id="-1001234")
        assert adapter.is_configured

    @pytest.mark.asyncio
    async def test_send_skips_when_not_configured(self):
        from cortex.notifications.adapters.telegram import TelegramAdapter

        adapter = TelegramAdapter(token="", chat_id="")
        # Should not raise even when unconfigured
        await adapter.send(make_event())

    @pytest.mark.asyncio
    async def test_send_posts_to_telegram_api(self):
        from cortex.notifications.adapters.telegram import TelegramAdapter

        adapter = TelegramAdapter(token="T0K3N", chat_id="-100123")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=AsyncMock(status_code=200, text="ok"))
            await adapter.send(make_event(severity=EventSeverity.ERROR))
            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["json"]["chat_id"] == "-100123"
            assert "parse_mode" in call_kwargs["json"]


# ─── MacOSAdapter tests ───────────────────────────────────────────────


class TestMacOSAdapter:
    @pytest.mark.asyncio
    async def test_send_on_non_darwin_is_noop(self):
        from cortex.notifications.adapters.macos import MacOSAdapter

        adapter = MacOSAdapter()
        with patch("sys.platform", "linux"):
            # Should not raise
            await adapter.send(make_event())
