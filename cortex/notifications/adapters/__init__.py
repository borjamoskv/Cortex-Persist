"""CORTEX — Notification Adapters registry."""

from cortex.notifications.adapters.base import BaseAdapter
from cortex.notifications.adapters.macos import MacOSAdapter
from cortex.notifications.adapters.telegram import TelegramAdapter

__all__ = [
    "BaseAdapter",
    "MacOSAdapter",
    "TelegramAdapter",
]
