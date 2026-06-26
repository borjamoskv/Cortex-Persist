#!/usr/bin/env python3
import asyncio
import json
import sys
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool, TextContent

# Ensure CORTEX paths are available
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(SCRIPTS_DIR))

# Import CORTEX modules
try:
    from agent_hound_omega import build_mythos_graph
    from strike_engine import execute_ouroboros_strike
except ImportError as e:
    print(f"Critical: Failed to import CORTEX modules: {e}")
    sys.exit(1)

app = Server("ouroboros-intelligence")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="intel_analyze_contract",
            description="High-exergy security audit for Solidity contracts using HOUND LangGraph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_code": {"type": "string", "description": "Solidity source code to analyze."},
                    "target_url": {"type": "string", "description": "Optional bounty or repository URL."}
                },
                "required": ["contract_code"]
            }
        ),
        Tool(
            name="intel_market_scan",
            description="Scans the mempool or markets for exergy opportunities (MEV/Arbitrage).",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["ARTEMIS", "MERCOR"], "description": "Scanning engine to use."}
                },
                "required": ["mode"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "intel_analyze_contract":
        code = arguments.get("contract_code")
        url = arguments.get("target_url", "https://local-audit.internal")
        
        print(f"[INTEL] Starting HOUND analysis on {url}...")
        graph = build_mythos_graph()
        result = graph.invoke({  # type: ignore
            "messages": [],
            "bounty_url": url,
            "target_code": code,
            "hypotheses": [],
            "scaffold_commands": [],
            "proof_of_concept": "",
            "is_verified": False,
            "iterations": 0
        })
        
        verdict = "C5-REAL" if result.get("is_verified") else "C5-PENDING"
        report = {
            "verdict": verdict,
            "hypotheses": result.get("hypotheses"),
            "iterations": result.get("iterations"),
            "STRIKE": result.get("proof_of_concept")[:200] + "..."  # type: ignore
        }
        return [TextContent(type="text", text=json.dumps(report, indent=2))]

    elif name == "intel_market_scan":
        mode = arguments.get("mode")
        print(f"[INTEL] Dispatching {mode} scanner...")
        res = execute_ouroboros_strike(mode, {"manual_trigger": True})
        return [TextContent(type="text", text=json.dumps(res, indent=2))]

    else:
        raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    from mcp.server.stdio import stdio_server
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    asyncio.run(main())
