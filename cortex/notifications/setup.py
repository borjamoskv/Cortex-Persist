"""CORTEX — Notification Bus startup wiring.

Called once at API/daemon startup to build and configure the process-level
NotificationBus from CortexConfig environment variables.

Usage (in cortex/api.py lifespan or daemon boot)::

    from cortex.notifications.setup import setup_notifications
    setup_notifications(cfg)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex.notifications.adapters.macos import MacOSAdapter
from cortex.notifications.adapters.telegram import TelegramAdapter
from cortex.notifications.bus import NotificationBus, get_notification_bus
from cortex.notifications.events import EventSeverity

if TYPE_CHECKING:
    from cortex.config import CortexConfig

logger = logging.getLogger("cortex.notifications.setup")


def setup_notifications(cfg: CortexConfig) -> NotificationBus:
    """Wire adapters from CortexConfig into the global NotificationBus.

    Args:
        cfg: A :class:`~cortex.config.CortexConfig` instance.

    Returns:
        The configured NotificationBus singleton.
    """
    bus = get_notification_bus()

    try:
        min_severity = EventSeverity(cfg.NOTIFICATIONS_MIN_SEVERITY)
    except ValueError:
        logger.warning(
            "Invalid CORTEX_NOTIFY_MIN_SEVERITY '%s', defaulting to 'warning'.",
            cfg.NOTIFICATIONS_MIN_SEVERITY,
        )
        min_severity = EventSeverity.WARNING

    # Telegram
    telegram = TelegramAdapter(
        token=cfg.TELEGRAM_TOKEN,
        chat_id=cfg.TELEGRAM_CHAT_ID,
    )
    bus.register(telegram, min_severity=min_severity)

    # macOS (always attempt — is_configured handles platform check)
    bus.register(MacOSAdapter(), min_severity=EventSeverity.WARNING)

    logger.info(
        "NotificationBus ready. Adapters: %s | Min severity: %s",
        bus.adapter_names,
        min_severity.value,
    )
    return bus
