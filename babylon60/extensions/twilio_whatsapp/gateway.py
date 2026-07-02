# [C5-REAL] Exergy-Maximized
"""
Twilio WhatsApp Gateway Implementation.
Enforces deterministic schemas and timeouts (C5-REAL).
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TwilioWhatsAppGateway:
    """
    Gateway to interact with Twilio WhatsApp API.
    Uses httpx directly to avoid external dependencies.
    """

    def __init__(self, account_sid: str, auth_token: str, sender: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.sender = sender.replace("whatsapp:", "")  # Normalize sender to plain number
        self.timeout = 5.0  # Deterministic timeout for exergy bounds

    async def send_message(self, to: str, body: str) -> dict[str, Any]:
        """
        Send a WhatsApp message via Twilio API.
        """
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

        # Ensure numbers are formatted with whatsapp: prefix for Twilio
        to_formatted = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
        from_formatted = f"whatsapp:{self.sender}"

        payload = {
            "From": from_formatted,
            "To": to_formatted,
            "Body": body,
        }

        auth = (self.account_sid, self.auth_token)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, data=payload, auth=auth)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Twilio API HTTP Error: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Twilio API Request Error: {e}")
                raise
