# [C5-REAL] Exergy-Maximized
"""MCP tools for CORTEX Twilio WhatsApp Integration."""

from __future__ import annotations

import logging
import os
from typing import Any

from babylon60.extensions.twilio_whatsapp.gateway import TwilioWhatsAppGateway

logger = logging.getLogger("babylon60.mcp_server.twilio_whatsapp")


def register_twilio_tools(mcp: Any, ctx: Any) -> None:
    """Register Twilio WhatsApp tools on the MCP server.

    Args:
        mcp: FastMCP server instance.
        ctx: MCPContext with engine reference.
    """

    @mcp.tool()
    async def send_twilio_whatsapp_message(to: str, text: str) -> dict:
        """Send a WhatsApp message via Twilio API.

        Args:
            to: The recipient phone number (e.g. '+34658010102').
            text: The text content of the message.

        Returns:
            A dictionary containing the API output status or error.
        """
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        sender = os.getenv("TWILIO_SENDER")

        if not all([account_sid, auth_token, sender]):
            return {
                "status": "error",
                "message": "Missing Twilio environment variables: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SENDER",
            }

        try:
            gateway = TwilioWhatsAppGateway(
                account_sid=account_sid, auth_token=auth_token, sender=sender
            )
            result = await gateway.send_message(to=to, body=text)
            return {"status": "success", "data": result}
        except Exception as e:  # noqa: BLE001
            logger.error(f"Twilio WhatsApp error: {e}")
            return {"status": "error", "message": str(e)}

    logger.debug("Registered twilio_whatsapp MCP tools")
