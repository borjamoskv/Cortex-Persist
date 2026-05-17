"""CORTEX — Webhook Notification Adapter."""

from __future__ import annotations

import logging

import httpx

from cortex.extensions.notifications.adapters.base import BaseAdapter
from cortex.extensions.notifications.events import CortexEvent

logger = logging.getLogger("cortex.extensions.notifications.adapters.webhook")


class WebhookAdapter(BaseAdapter):
    """Deliver notifications via HTTP POST to a configured Webhook URL."""

    name: str = "webhook"

    def __init__(self, webhook_url: str) -> None:
        """Initialize with a webhook URL."""
        self.webhook_url = webhook_url

    @property
    def is_configured(self) -> bool:
        """Check if webhook_url is set."""
        return bool(self.webhook_url)

    async def send(self, event: CortexEvent) -> None:
        """Send the notification via HTTP POST.

        Will not raise exceptions; failures are logged.
        """
        if not self.is_configured:
            return

        payload = {
            "title": event.title,
            "body": event.body,
            "severity": event.severity.value,
            "source": event.source,
        }
        if event.project:
            payload["project"] = event.project
        if event.tags:
            payload["tags"] = event.tags

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=5.0,
                )
                resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send webhook notification: %s", exc)
