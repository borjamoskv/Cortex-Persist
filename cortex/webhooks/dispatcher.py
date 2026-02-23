"""
CORTEX v6 — Webhooks Dispatcher.

Dispatches events from the Distributed Event Bus to external
clients via HTTPS Webhooks (for integrations like Zapier/Slack).
"""

import logging
from typing import Any

from cortex.events.bus import DistributedEventBus

logger = logging.getLogger("cortex.webhooks")


class WebhookDispatcher:
    """Manages external webhook subscriptions per tenant."""

    __slots__ = ("_bus", "_endpoints")

    def __init__(self, bus: DistributedEventBus) -> None:
        self._bus = bus
        self._endpoints: dict[str, list[str]] = {}  # tenant_id -> list of URLs

    def register_endpoint(self, tenant_id: str, url: str) -> None:
        """Register a new webhook URL for a specific tenant."""
        if tenant_id not in self._endpoints:
            self._endpoints[tenant_id] = []
        if url not in self._endpoints[tenant_id]:
            self._endpoints[tenant_id].append(url)
            logger.info("Registered webhook %s for tenant %s", url, tenant_id)

    async def dispatch_event(
        self, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Trigger webhooks for a tenant on specific events."""
        urls = self._endpoints.get(tenant_id, [])
        if not urls:
            return

        # In v6 full implementation, this will use httpx to POST payloads,
        # with retry logic, exponential backoff, and signature verification (HMAC).
        for url in urls:
            logger.debug(
                "Mock Dispatch %s to %s with payload keys: %s",
                event_type,
                url,
                payload.keys(),
            )
