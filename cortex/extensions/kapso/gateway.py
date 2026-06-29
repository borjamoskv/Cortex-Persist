import logging
from typing import Any

import httpx

from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class KapsoGateway:
    """
    Gateway to interact with Kapso (WhatsApp API).
    Enforces deterministic schemas and timeouts (C5-REAL).
    """
    def __init__(self, api_key: str, phone_number_id: str, base_url: str = "https://api.kapso.ai/v1"):
        self.api_key = api_key
        self.phone_number_id = phone_number_id
        self.base_url = base_url.rstrip("/")
        self.timeout = 5.0 # Deterministic timeout for exergy bounds

    async def send_message(self, message: WhatsAppMessage) -> dict[str, Any]:
        """
        Send a WhatsApp message via Kapso API.
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = message.model_dump(exclude_none=True)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Kapso API HTTP Error: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Kapso API Request Error: {e}")
                raise
