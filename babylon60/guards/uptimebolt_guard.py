# [C5-REAL] Exergy-Maximized
"""
UptimeBolt Deployment Safety Guard (SAGA-1).

Integrates the `is_safe_to_deploy` tool from UptimeBolt MCP Server directly
into the CORTEX Write-Path contract.

Author: borjamoskv
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("cortex.guards.uptimebolt_guard")


def enforce_deploy_safety(payload_str: str) -> None:
    """Enforce deployment safety using UptimeBolt MCP.
    
    If the payload is a deployment or bridge operation, it queries the UptimeBolt
    MCP server. If the risk is high, it raises ValueError to abort the SAGA.
    
    Operates in 'Fail Open' mode: if UPTIMEBOLT_API_KEY is missing, it bypasses
    the check to avoid friction in local development environments.
    """
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        # Not a valid JSON, skip this guard
        return

    if not isinstance(payload, dict):
        return

    fact_type = payload.get("fact_type", "")
    if fact_type not in ("deploy", "bridge", "UI_ACTION"):
        # We only guard deployment-related mutations
        return

    api_key = os.environ.get("UPTIMEBOLT_API_KEY")
    if not api_key:
        logger.debug("[UptimeBoltGuard] UPTIMEBOLT_API_KEY not set. Bypassing deploy safety check (Fail Open).")
        return

    mcp_url = os.environ.get("UPTIMEBOLT_MCP_URL", "http://localhost:3100/mcp")
    service_name = payload.get("project", "default-cortex-service")

    logger.info(f"🛡️ [UptimeBoltGuard] Verifying deployment safety for service: {service_name}")

    mcp_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "is_safe_to_deploy",
            "arguments": {"service_name": service_name}
        }
    }

    req = urllib.request.Request(
        mcp_url,
        data=json.dumps(mcp_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": api_key,
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            # MCP Tool Call responses are typically in result.content[0].text
            result_obj = res_data.get("result", {})
            if result_obj.get("isError"):
                logger.error(f"[UptimeBoltGuard] MCP returned error: {result_obj}")
                # Fail open on MCP internal errors unless strict
                return
                
            content = result_obj.get("content", [])
            if not content:
                logger.warning("[UptimeBoltGuard] Empty response from MCP. Bypassing.")
                return
                
            text_response = content[0].get("text", "{}")
            try:
                safety_data = json.loads(text_response)
            except json.JSONDecodeError:
                safety_data = {"recommendation": "proceed"} # Assume it's prose?
                
            recommendation = safety_data.get("recommendation", "proceed")
            
            if recommendation not in ("proceed", "proceed_with_caution"):
                risk = safety_data.get("risk_level", "high")
                err_msg = f"SAGA-1 Rejection by UptimeBolt: Risk is {risk.upper()} ({recommendation})"
                logger.error(f"❌ [UptimeBoltGuard] {err_msg}")
                raise ValueError(err_msg)
                
            logger.info(f"✅ [UptimeBoltGuard] Deployment safe to proceed. Recommendation: {recommendation}")

    except urllib.error.URLError as e:
        logger.warning(f"⚠️ [UptimeBoltGuard] Connection to UptimeBolt MCP failed: {e}. Bypassing (Fail Open).")
    # Let ValueError bubble up to trigger SAGA-1 rollback
