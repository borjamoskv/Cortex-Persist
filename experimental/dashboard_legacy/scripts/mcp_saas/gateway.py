import os

from dotenv import load_dotenv

load_dotenv()
import asyncio
import json
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

# Ensure parent is in path for auth/db imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "scripts"))

from native_paths import resolve_project_script

try:
    from db import CONFIG, record_memory_event
    from mcp_saas.auth import deduct_exergy, verify_and_gate
except ImportError as e:
    print(f"[!] Import error: {e}")
    sys.exit(1)

app = FastAPI(title="Sovereign MCP Gateway — The Membrane")

# Registry of active server instances using explicit script resolution.
CAPABILITY_SERVERS = {
    "foundry": resolve_project_script(
        "mcp_saas/servers/foundry.py",
        "CORTEX_MCP_FOUNDRY_SERVER",
    ),
    "vsa": resolve_project_script(
        "mcp_saas/servers/vsa_server.py",
        "CORTEX_MCP_VSA_SERVER",
    ),
    "intel": resolve_project_script(
        "mcp_saas/servers/intelligence.py",
        "CORTEX_MCP_INTEL_SERVER",
    ),
}

CAPABILITY_COSTS = {
    "intel": 5.0,
    "foundry": 1.0,
    "vsa": 1.5
}


def _auth_error_status(auth_result: dict) -> int:
    """Map deterministic auth failures to transport-level status codes."""
    return 503 if auth_result.get("error") == "TOKEN_STORE_UNAVAILABLE" else 403

@app.get("/api/mcp/sse")
async def mcp_sse_endpoint(request: Request, token: str = Query(...)):
    """Establish a Sovereign MCP SSE stream."""
    auth = verify_and_gate(token)
    if not auth["valid"]:
        raise HTTPException(status_code=_auth_error_status(auth), detail=auth["error"])
    
    tenant_id = auth["tenant_id"]
    print(f"[*] SSE Established for {tenant_id}")
    
    async def event_generator():
        # MCP Initialized event
        yield {
            "event": "message",
            "id": "init",
            "data": json.dumps({"jsonrpc": "2.0", "method": "mcp.initialized", "params": {}})
        }
        
        # Keep-alive loop or proxying events from underlying processes
        while True:
            if await request.is_disconnected():
                print(f"[*] {tenant_id} Disconnected")
                break
            await asyncio.sleep(30) # Heartbeat
            yield { "event": "ping", "data": "ping" }

    return EventSourceResponse(event_generator())

@app.post("/api/mcp/message")
async def mcp_post_message(request: Request, token: str = Query(...)):
    """Standard MCP message endpoint (Tool calls/Resource Reads)."""
    auth = verify_and_gate(token)
    if not auth["valid"]:
        raise HTTPException(status_code=_auth_error_status(auth), detail=auth["error"])
    
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    
    # Audit to Ledger
    record_memory_event(
        "mcp_gateway", 
        f"MCP Call: {method}", 
        f"req_{auth['tenant_id']}", 
        {"method": method, "params": params}
    )
    
    # --- CAPABILITY GATE ---
    if method == "tools/call":
        tool_name = params.get("name", "")
        if not tool_name:
            return {"error": "Missing tool name"}
        capability = tool_name.split("_")[0]
        
        check = verify_and_gate(token, capability=capability)
        if not check["valid"]:
            return {"error": check["error"]}
            
        print(f"[*] {auth['tenant_id']} calling {tool_name}")

        # --- C5-REAL EXECUTION: Proxy to Native STDIO Server ---
        server_script = CAPABILITY_SERVERS.get(capability)
        if not server_script:
            return {"error": "Server not configured for capability"}

        # Dynamic Exergy Drain Mechanism
        cost = CAPABILITY_COSTS.get(capability, 1.0)
        new_balance = deduct_exergy(token, cost)
            
        try:
            from mcp.client.session import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client
            
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[str(server_script)],
                env=os.environ.copy()
            )
            
            # Spin up the target server, perform handshake, execute, return
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tool_result = await session.call_tool(tool_name, params.get("arguments", {}))
                    
                    # Transform MCP result format back to JSON-RPC mapping
                    content = [{"type": c.type, "text": getattr(c, "text", str(c))} for c in tool_result.content]
                    
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": content,
                    "exergy_remaining": new_balance
                },
                "id": body.get("id")
            }
        except Exception as e:
            print(f"[!] REAL_EXECUTION_ERROR: {e}")
            return {"error": f"C5 Execution Failed: {str(e)}"}

    return {"jsonrpc": "2.0", "result": "RECIEVED", "id": body.get("id")}


if __name__ == "__main__":
    port = CONFIG.get("mcp_gateway", {}).get("port", 8001)
    print(f"∴ SOVEREIGN MCP GATEWAY booting on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
