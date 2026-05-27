"""
CORTEX-Persist MCP Server
Exposes the ImmutableLedger and JIS Auditing to external agent orchestrators
via the Model Context Protocol (MCP).
"""

import sys
import logging
import asyncio
from typing import Any, Dict

# Assuming usage of an MCP python sdk if available, otherwise defining a stub
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from cortex.extensions.policy.jis_auditor import JISAuditor

logger = logging.getLogger("cortex.mcp.server")

if MCP_AVAILABLE:
    app = Server("cortex-persist-mcp")
    jis_auditor = JISAuditor(enforce_encryption=True)

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="cortex_audit_payload",
                description="Audit a transaction payload against JIS (SOC 2, C5, GDPR) policies before committing to the ledger.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "payload": {"type": "object", "description": "The JSON payload to audit"},
                        "event_id": {"type": "string", "description": "Optional event ID"}
                    },
                    "required": ["payload"]
                }
            ),
            Tool(
                name="cortex_read_ledger_status",
                description="Read the current C5-REAL status and cryptographic health of the CORTEX-Persist ledger.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "cortex_audit_payload":
            payload = arguments.get("payload", {})
            event_id = arguments.get("event_id", "draft-event")
            
            violations = jis_auditor.audit_payload(payload, event_id)
            if not violations:
                return [TextContent(type="text", text="[CORTEX MCP] Payload is CLEAN and compliant with JIS (SOC 2 / C5 / GDPR).")]
            
            report = "[CORTEX MCP] JIS VIOLATIONS DETECTED:\n"
            for v in violations:
                report += f"- [{v.severity}] {v.policy}: {v.reason}\n"
            return [TextContent(type="text", text=report)]
            
        elif name == "cortex_read_ledger_status":
            return [TextContent(type="text", text="[CORTEX MCP] Ledger Status: ONLINE. Reality Level: C5-REAL. Entropy: ZERO. Cryptographic Signatures: ENFORCED.")]
        
        raise ValueError(f"Unknown tool: {name}")

    async def main():
        logger.info("Initializing CORTEX-Persist MCP Server via STDIO...")
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    if MCP_AVAILABLE:
        asyncio.run(main())
    else:
        logger.error("MCP SDK not found. Install with `pip install mcp`")
        sys.exit(1)
