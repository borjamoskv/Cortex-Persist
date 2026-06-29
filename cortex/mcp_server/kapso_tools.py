# [C5-REAL] Exergy-Maximized
"""MCP tools for CORTEX Kapso WhatsApp Integration.

Registers kapso tools on a FastMCP server so AI agents
can send and manage WhatsApp messages via @kapso/cli.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger("cortex.mcp_server.kapso")


def register_kapso_tools(mcp: Any, ctx: Any) -> None:
    """Register Kapso CLI tools on the MCP server.

    Args:
        mcp: FastMCP server instance.
        ctx: MCPContext with engine reference.
    """

    @mcp.tool()
    async def send_whatsapp_message(to: str, text: str) -> dict:
        """Send a WhatsApp message via Kapso CLI.

        Args:
            to: The recipient phone number (e.g. '+34600000000').
            text: The text content of the message.

        Returns:
            A dictionary containing the CLI output (usually a message ID) or error.
        """
        try:
            # We use npx to ensure it runs the locally installed @kapso/cli
            # or fetches it seamlessly if not globally installed.
            cmd = [
                "npx",
                "@kapso/cli",
                "whatsapp",
                "messages",
                "send",
                "--to",
                to,
                "--text",
                text,
                "--output",
                "json",
            ]
            
            logger.debug(f"Executing kapso command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            try:
                # Try parsing as JSON since we requested --output=json
                return {"status": "success", "data": json.loads(result.stdout)}
            except json.JSONDecodeError:
                # Fallback to plain text if JSON parsing fails
                return {"status": "success", "data": result.stdout}

        except subprocess.CalledProcessError as e:
            logger.error(f"Kapso CLI error: {e.stderr}")
            return {"status": "error", "message": e.stderr}
        except Exception as e:
            logger.error(f"Unexpected error executing Kapso: {e}")
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def list_whatsapp_messages() -> dict:
        """List recent WhatsApp messages in the current Kapso project.

        Returns:
            A dictionary containing the parsed list of messages or error.
        """
        try:
            cmd = [
                "npx",
                "@kapso/cli",
                "whatsapp",
                "messages",
                "list",
                "--output",
                "json",
            ]
            
            logger.debug("Executing kapso list command")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            try:
                return {"status": "success", "data": json.loads(result.stdout)}
            except json.JSONDecodeError:
                return {"status": "success", "data": result.stdout}

        except subprocess.CalledProcessError as e:
            logger.error(f"Kapso CLI list error: {e.stderr}")
            return {"status": "error", "message": e.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    logger.debug("Registered kapso MCP tools")
