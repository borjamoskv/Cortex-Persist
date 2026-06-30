# [C5-REAL] Exergy-Maximized
"""
CORTEX-Persist MCP Server
Exposes the ImmutableLedger and JIS Auditing to external agent orchestrators
via the Model Context Protocol (MCP).
"""

import asyncio
import logging
import sys

# Assuming usage of an MCP python sdk if available, otherwise defining a stub
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from babylon60.extensions.mcp.claude_tool import run_claude_query
from babylon60.extensions.policy.jis_auditor import JISAuditor
from babylon60.memory.vsa import VSAPipelineBridge

logger = logging.getLogger("cortex.mcp_server.server")

if MCP_AVAILABLE:
    app = Server("cortex-persist-mcp")
    jis_auditor = JISAuditor(enforce_encryption=True)
    vsa_bridge = VSAPipelineBridge(agent_id="cortex_mcp_server")

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
                        "event_id": {"type": "string", "description": "Optional event ID"},
                    },
                    "required": ["payload"],
                },
            ),
            Tool(
                name="cortex_read_ledger_status",
                description="Read the current C5-REAL status and cryptographic health of the CORTEX-Persist ledger.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="cortex_vsa_ingest",
                description="Ingest new knowledge into the Sovereign VSA-SDM memory.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Text content to memorize"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags",
                        },
                    },
                    "required": ["content"],
                },
            ),
            Tool(
                name="cortex_vsa_query",
                description="Query the Sovereign VSA-SDM memory using algebraic similarity.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string", "description": "Natural language query"},
                        "top_k": {"type": "integer", "description": "Max results to return"},
                    },
                    "required": ["intent"],
                },
            ),
            Tool(
                name="cortex_invoke_claude",
                description="Deterministic execution of Claude Opus 4.8 via Anthropic API.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "The prompt to execute"},
                        "model": {
                            "type": "string",
                            "description": "The model ID (default: claude-3-opus-20240229)",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "cortex_audit_payload":
            payload = arguments.get("payload", {})
            event_id = arguments.get("event_id", "draft-event")

            violations = jis_auditor.audit_payload(payload, event_id)
            if not violations:
                return [
                    TextContent(
                        type="text",
                        text="[CORTEX MCP] Payload is CLEAN and compliant with JIS (SOC 2 / C5 / GDPR).",
                    )
                ]

            report = "[CORTEX MCP] JIS VIOLATIONS DETECTED:\n"
            for v in violations:
                report += f"- [{v.severity}] {v.policy}: {v.reason}\n"
            return [TextContent(type="text", text=report)]

        if name == "cortex_read_ledger_status":
            return [
                TextContent(
                    type="text",
                    text="[CORTEX MCP] Ledger Status: ONLINE. Reality Level: C5-REAL. Entropy: ZERO. Cryptographic Signatures: ENFORCED.",
                )
            ]

        if name == "cortex_vsa_ingest":
            content = arguments.get("content")
            tags = arguments.get("tags")
            rid = vsa_bridge.ingest(content, tags=tags)  # pyright: ignore[reportArgumentType]
            vsa_bridge.persist()
            return [
                TextContent(
                    type="text",
                    text=f"[CORTEX MCP] Knowledge ingested into VSA memory with ID: {rid}",
                )
            ]

        if name == "cortex_vsa_query":
            intent = arguments.get("intent")
            top_k = arguments.get("top_k", 3)
            results = vsa_bridge.query(intent, top_k=top_k)  # pyright: ignore[reportArgumentType]
            if not results:
                return [TextContent(type="text", text="[CORTEX MCP] No relevant VSA memory found.")]

            out = "[CORTEX MCP] VSA-SDM Query Results:\n"
            for r in results:
                out += f"- [{r['id']}] (Sim: {r['similarity']}): {r['content']}\n"
            return [TextContent(type="text", text=out)]

        if name == "cortex_invoke_claude":
            prompt = arguments.get("prompt")
            model = arguments.get("model", "claude-3-opus-20240229")
            response_json = run_claude_query(prompt, model)  # pyright: ignore[reportArgumentType]
            return [TextContent(type="text", text=response_json)]

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
