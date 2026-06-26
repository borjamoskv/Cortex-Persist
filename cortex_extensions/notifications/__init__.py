# [C5-REAL] Exergy-Maximized
"""CORTEX - Notification Bus.

Pluggable notification layer that delivers CORTEX events to external
channels (Telegram, macOS, Slack, webhooks, etc.).

Usage::

    from cortex_extensions.notifications import get_notification_bus, CortexEvent, EventSeverity

    bus = get_notification_bus()
    await bus.emit(CortexEvent(
        severity=EventSeverity.WARNING,
        title="Ghost backlog growing",
        body="23 unresolved ghosts detected across 4 projects.",
        source="ghost_monitor",
    ))
"""

from cortex_extensions.notifications.bus import NotificationBus, get_notification_bus
from cortex_extensions.notifications.events import CortexEvent, EventSeverity

__all__ = [
    "CortexEvent",
    "EventSeverity",
    "NotificationBus",
    "get_notification_bus",
]
