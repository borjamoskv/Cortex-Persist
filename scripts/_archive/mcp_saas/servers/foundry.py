import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
)
from pydantic import AnyUrl

# Design Tokens (Noir 2026)
NOIR_2026_TOKENS = {
    "colors": {
        "background": "#0A0A0A",
        "primary": "#2B3BE5",
        "accent": "#00FF41",
        "surface": "#1A1A1A",
        "text": "#E0E0E0"
    },
    "typography": {
        "font_family": "Inter, Roboto, sans-serif",
        "h1": {"size": "3rem", "weight": "700"},
        "body": {"size": "1rem", "weight": "400"}
    }
}

app = Server("Aesthetic-Foundry")

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available design tokens as resources."""
    return [
        Resource(
            uri=AnyUrl("foundry://tokens/noir-2026"),
            name="Noir 2026 Design Tokens",
            description="The core CSS/JSON tokens for the Sovereign design system.",
            mimeType="application/json",
        )
    ]

@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Read design tokens."""
    if uri == AnyUrl("foundry://tokens/noir-2026"):
        return json.dumps(NOIR_2026_TOKENS, indent=2)
    raise ValueError(f"Unknown resource: {uri}")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available design tools."""
    return [
        Tool(
            name="foundry_palette",
            description="Get the Noir 2026 color palette for a given context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "e.g., 'dark_mode', 'industrial_noir'"}
                },
            },
        ),
        Tool(
            name="foundry_audit",
            description="Audit a code snippet (CSS/HTML) for Noir 2026 compliance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The code to audit."}
                },
                "required": ["code"]
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute design tools."""
    if name == "foundry_palette":
        return [TextContent(type="text", text=json.dumps(NOIR_2026_TOKENS["colors"], indent=2))]
    
    if name == "foundry_audit":
        code = arguments.get("code", "")
        # synthetic audit logic
        issues = []
        if "#ff0000" in code.lower():
            issues.append("[CRITICAL] Generic red detected. Use #D32F2F for sovereign alerts.")
        if "border-radius: 0" not in code.lower() and "工业" in code: # Industrial noir vibes
             issues.append("[WARNING] Sharp corners preferred for industrial noir.")
             
        report = "Audit Results: PASS" if not issues else "Audit Results: FAIL\n" + "\n".join(issues)
        return [TextContent(type="text", text=report)]
        
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
