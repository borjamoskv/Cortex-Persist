"""CORTEX — Notification Bus (core orchestrator).

The NotificationBus is the single point of dispatch for all CORTEX events.
It manages a registry of pluggable adapters and fans out events concurrently.

Design principles:
- Fire-and-forget: adapters never block or raise
- Severity filtering: each adapter can declare a minimum severity threshold
- Singleton: use get_notification_bus() for the process-level instance
- Zero new deps: uses asyncio + httpx (already in project)

Wire-up::

    # In cortex/api.py startup:
    from cortex.notifications import get_notification_bus
    bus = get_notification_bus()
    bus.register(TelegramAdapter())
    bus.register(MacOSAdapter())
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from cortex.notifications.events import CortexEvent, EventSeverity

if TYPE_CHECKING:
    from cortex.notifications.adapters.base import BaseAdapter

logger = logging.getLogger("cortex.notifications.bus")

_SEVERITY_ORDER = [s.value for s in EventSeverity]


class NotificationBus:
    """Concurrent fan-out notification bus with pluggable adapters.

    Example::

        bus = NotificationBus()
        bus.register(TelegramAdapter(), min_severity=EventSeverity.WARNING)
        bus.register(MacOSAdapter(), min_severity=EventSeverity.INFO)

        await bus.emit(CortexEvent(
            severity=EventSeverity.ERROR,
            title="Test suite failed",
            body="42 tests failed in cortex/tests/",
            source="pytest",
            project="cortex",
        ))
    """

    def __init__(self) -> None:
        # list of (adapter, min_severity_index)
        self._adapters: list[tuple[BaseAdapter, int]] = []

    def register(
        self,
        adapter: BaseAdapter,
        *,
        min_severity: EventSeverity = EventSeverity.INFO,
    ) -> None:
        """Register an adapter with an optional minimum severity threshold.

        Args:
            adapter:      An initialized adapter instance.
            min_severity: Events below this severity are not delivered.
        """
        if not adapter.is_configured:
            logger.info(
                "Adapter '%s' skipped — not configured (missing credentials?).",
                adapter.name,
            )
            return

        threshold = _SEVERITY_ORDER.index(min_severity.value)
        self._adapters.append((adapter, threshold))
        logger.info("Registered adapter '%s' (min: %s).", adapter.name, min_severity.value)

    async def emit(self, event: CortexEvent) -> None:
        """Fan out event to all eligible adapters concurrently.

        Adapters that throw are logged but never re-raised.
        """
        if not self._adapters:
            return

        event_level = _SEVERITY_ORDER.index(event.severity.value)
        eligible = [a for a, threshold in self._adapters if event_level >= threshold]

        if not eligible:
            return

        await asyncio.gather(
            *[self._safe_send(adapter, event) for adapter in eligible],
            return_exceptions=True,
        )

    async def _safe_send(self, adapter: BaseAdapter, event: CortexEvent) -> None:
        """Wrap adapter.send() so exceptions never escape the bus."""
        try:
            await adapter.send(event)
        except Exception as exc:  # noqa: BLE001
            logger.error("Adapter '%s' raised unexpectedly: %s", adapter.name, exc)

    @property
    def adapter_names(self) -> list[str]:
        """Names of all registered (configured) adapters."""
        return [a.name for a, _ in self._adapters]

    def __repr__(self) -> str:
        return f"NotificationBus(adapters={self.adapter_names})"


# ─── Process-level singleton ─────────────────────────────────────────

_bus: NotificationBus | None = None


def get_notification_bus() -> NotificationBus:
    """Return the process-level NotificationBus singleton.

    First call creates an unconfigured bus. Register adapters at startup.
    """
    global _bus
    if _bus is None:
        _bus = NotificationBus()
    return _bus


def reset_notification_bus() -> None:
    """Reset the singleton (test isolation only)."""
    global _bus
    _bus = None
