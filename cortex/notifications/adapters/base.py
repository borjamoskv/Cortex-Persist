"""CORTEX — Notification Adapter base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from cortex.notifications.events import CortexEvent


class BaseAdapter(ABC):
    """Abstract base for all notification adapters.

    Each adapter is responsible for delivering a :class:`CortexEvent`
    to a specific channel (Telegram, macOS, Slack, webhook, etc.).

    Adapters are fire-and-forget — they MUST swallow all exceptions
    internally and log failures rather than propagating them. The bus
    should never fail because one adapter is down.
    """

    name: str = "base"

    @abstractmethod
    async def send(self, event: CortexEvent) -> None:
        """Deliver the event to the channel.

        Must not raise. Log and return on failure.
        """

    @property
    def is_configured(self) -> bool:
        """Return True if the adapter has the required credentials/config."""
        return True
