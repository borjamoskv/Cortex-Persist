"""CORTEX — Notification Adapters registry."""

from cortex.extensions.notifications.adapters.base import BaseAdapter
from cortex.extensions.notifications.adapters.macos import MacOSAdapter
from cortex.extensions.notifications.adapters.telegram import TelegramAdapter

__all__ = [
    "BaseAdapter",
    "MacOSAdapter",
    "TelegramAdapter",
]
