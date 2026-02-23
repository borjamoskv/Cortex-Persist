"""CORTEX — Telegram Notification Adapter.

Delivers events to a Telegram chat using the Bot API.
No dependencies beyond httpx (already in the project).

Setup::

    export CORTEX_TELEGRAM_TOKEN="7xxxxxxxx:AAxxxxxx"
    export CORTEX_TELEGRAM_CHAT_ID="-1001234567890"   # group or user chat ID
"""

from __future__ import annotations

import logging
import os

import httpx

from cortex.notifications.adapters.base import BaseAdapter
from cortex.notifications.events import CortexEvent

logger = logging.getLogger("cortex.notifications.telegram")

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramAdapter(BaseAdapter):
    """Sends CortexEvents to a Telegram chat."""

    name = "telegram"

    def __init__(
        self,
        token: str = "",
        chat_id: str = "",
    ) -> None:
        self._token = token or os.environ.get("CORTEX_TELEGRAM_TOKEN", "")
        self._chat_id = chat_id or os.environ.get("CORTEX_TELEGRAM_CHAT_ID", "")

    @property
    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    async def send(self, event: CortexEvent) -> None:
        """POST event to Telegram Bot API."""
        if not self.is_configured:
            logger.debug("TelegramAdapter: not configured, skipping.")
            return

        url = _TELEGRAM_API.format(token=self._token)
        payload = {
            "chat_id": self._chat_id,
            "text": event.format_text(),
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.warning(
                        "Telegram delivery failed: HTTP %d — %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                else:
                    logger.debug("Telegram event delivered: %s", event.title)
        except httpx.RequestError as exc:
            logger.error("Telegram network error: %s", exc)
