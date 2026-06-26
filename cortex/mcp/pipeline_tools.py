# [C5-REAL] Exergy-Maximized
"""MCP Pipeline Tools - Expose E2E Pipeline as MCP Tools.

Registers cortex_run, cortex_pipeline_status, and cortex_pipeline_history
as MCP tools, enabling any external agent to execute sovereign missions
through the deterministic pipeline.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cortex.pipeline import (
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
)

if TYPE_CHECKING:
    from cortex.mcp.server import _MCPContext

logger = logging.getLogger("cortex.mcp.pipeline")

# ── Shared pipeline bridge (singleton per server lifecycle) ──────────

_bridge_instance = None
_bridge_lock = None


async def _get_bridge(db_path: str | Path | None = None):
    """Get or create the shared CortexPipelineBridge singleton."""
    global _bridge_instance, _bridge_lock
    import asyncio

    if _bridge_lock is None:
        _bridge_lock = asyncio.Lock()

    async with _bridge_lock:
        if _bridge_instance is None:
            from cortex.pipeline.bridge import CortexPipelineBridge

            if db_path:
                _bridge_instance = CortexPipelineBridge(db_path=db_path)
            else:
                _bridge_instance = CortexPipelineBridge()
            await _bridge_instance.initialize()
            logger.info("[MCP] Pipeline bridge initialized")
        return _bridge_instance


def _result_to_dict(result: PipelineResult) -> dict[str, Any]:
    """Convert PipelineResult to MCP-safe serializable dict."""
    output = result.output
    content = ""
    provider = "unknown"

    if isinstance(output, dict):
        content = output.get("content", "")
        provider = output.get("provider", "unknown")
        if output.get("multi_agent"):
            contents = []
            for r in output.get("results", []):
                agent_id = r.get("agent_id", "?")
                c = r.get("content", r.get("error", ""))
                contents.append(f"[{agent_id}] {c}")
            content = "\n\n".join(contents)
    elif isinstance(output, str):
        content = output

    return {
        "mission_id": result.mission_id,
        "status": result.status.value,
        "content": content,
        "provider": provider,
        "latency_ms": round(result.latency_ms, 1),
        "cost_usd": result.cost_usd,
        "agents": result.agent_chain,
        "context_sources": len(result.context_used),
        "ledger_hash": result.ledger_hash[:16] + "..." if result.ledger_hash else "",
        "stages": [
            {
                "name": s.stage.value,
                "latency_ms": round(s.latency_ms, 1),
                "error": s.error,
            }
            for s in result.stages
        ],
        "error": result.error,
    }


# ── Internal Logic Delegates ──────────────────────────────────────────


async def _execute_run(
    ctx: _MCPContext | None,
    intent: str,
    budget_usd: float,
    delivery: str,
    context_hints: str,
    priority: int,
) -> str:
    if not intent or not intent.strip():
        return json.dumps({"error": "Empty intent", "status": "failed"})

    try:
        hints = json.loads(context_hints) if context_hints else []
    except (json.JSONDecodeError, TypeError):
        hints = []

    delivery_map = {
        "memory": DeliveryType.MEMORY,
        "stdout": DeliveryType.STDOUT,
        "file": DeliveryType.FILE,
        "webhook": DeliveryType.WEBHOOK,
        "mcp": DeliveryType.MCP,
    }
    delivery_type = delivery_map.get(delivery.lower(), DeliveryType.MEMORY)

    request = PipelineRequest(
        intent=intent.strip(),
        context_hints=hints,
        budget_limit_usd=max(budget_usd, 0.001),
        delivery=DeliveryTarget(type=delivery_type),
        priority=priority,
    )

    db_path = ctx.cfg.db_path if ctx else None
    bridge = await _get_bridge(db_path)

    try:
        result = await bridge.run(request)
        return json.dumps(_result_to_dict(result), indent=2, default=str)
    except Exception as e:
        logger.error("[MCP] Pipeline execution failed: %s", e)
        return json.dumps({"error": str(e), "status": "failed", "mission_id": request.mission_id})


async def _execute_run_async(
    ctx: _MCPContext | None,
    intent: str,
    budget_usd: float,
    timeout_s: float,
    context_hints: str,
    priority: int,
) -> str:
    if not intent or not intent.strip():
        return json.dumps({"error": "Empty intent", "status": "failed"})

    try:
        hints = json.loads(context_hints) if context_hints else []
    except (json.JSONDecodeError, TypeError):
        hints = []

    request = PipelineRequest(
        intent=intent.strip(),
        context_hints=hints,
        budget_limit_usd=max(budget_usd, 0.001),
        delivery=DeliveryTarget(type=DeliveryType.MEMORY),
        priority=priority,
        timeout_s=timeout_s,
    )

    db_path = ctx.cfg.db_path if ctx else None
    bridge = await _get_bridge(db_path)

    try:
        result = await bridge.run_async(request)
        return json.dumps(_result_to_dict(result), indent=2, default=str)
    except Exception as e:
        logger.error("[MCP] Async pipeline failed: %s", e)
        return json.dumps({"error": str(e), "status": "failed", "mission_id": request.mission_id})


async def _execute_cancel(ctx: _MCPContext | None, mission_id: str) -> str:
    if not mission_id or not mission_id.strip():
        return json.dumps({"error": "Empty mission_id", "status": "failed"})

    db_path = ctx.cfg.db_path if ctx else None
    bridge = await _get_bridge(db_path)

    try:
        if hasattr(bridge, "cancel"):
            cancelled = await bridge.cancel(mission_id.strip())
            return json.dumps(
                {
                    "mission_id": mission_id.strip(),
                    "cancelled": cancelled,
                    "status": "cancelled" if cancelled else "not_found",
                }
            )
        return json.dumps(
            {
                "mission_id": mission_id.strip(),
                "cancelled": False,
                "status": "cancel_not_supported",
                "note": "Bridge does not support cancellation yet",
            }
        )
    except Exception as e:
        logger.error("[MCP] Cancel failed: %s", e)
        return json.dumps({"error": str(e), "status": "failed"})


def _get_status() -> str:
    ledger_path = os.path.expanduser("~/.cortex/pipeline_ledger.jsonl")
    entries = []

    if os.path.exists(ledger_path):
        with open(ledger_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    recent = entries[-10:] if entries else []
    status = {
        "pipeline": "operational",
        "total_missions": len(entries),
        "recent_missions": [
            {
                "mission_id": e.get("mission_id", "?"),
                "hash": e.get("result_hash", "")[:16] + "...",
                "timestamp": e.get("timestamp", 0),
            }
            for e in reversed(recent)
        ],
    }

    try:
        from cortex_extensions.swarm.budget import get_budget_manager

        bm = get_budget_manager()
        budget_info = bm.get_remaining_budget()
        status["budget"] = {
            "remaining_usd": budget_info.get("remaining", 0),
            "total_spent_usd": budget_info.get("spent", 0),
        }
    except (ImportError, Exception):
        status["budget"] = "unavailable"

    return json.dumps(status, indent=2, default=str)


def _get_history(limit: int) -> str:
    ledger_path = os.path.expanduser("~/.cortex/pipeline_ledger.jsonl")

    if not os.path.exists(ledger_path):
        return json.dumps({"entries": [], "total": 0})

    entries = []
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    capped = min(max(limit, 1), 100)
    recent = list(reversed(entries[-capped:]))

    return json.dumps({"entries": recent, "total": len(entries)}, indent=2, default=str)


# ── Tool Registration ────────────────────────────────────────────────


def register_pipeline_tools(mcp, ctx: _MCPContext | None = None) -> None:
    """Register E2E pipeline tools on the MCP server."""

    @mcp.tool()
    async def cortex_run(
        intent: str,
        budget_usd: float = 0.10,
        delivery: str = "memory",
        context_hints: str = "[]",
        priority: int = 1,
    ) -> str:
        """Execute a sovereign E2E mission through the CORTEX pipeline.

        Stages: Ingress → Context → Plan → Execute → Persist → Egress.
        All results are hash-chained to the pipeline audit ledger.

        Args:
            intent: Natural language instruction for the mission.
            budget_usd: Maximum spend in USD (default: $0.10).
            delivery: Target output: "memory", "stdout", "file".
            context_hints: JSON array of knowledge item IDs to prioritize.
            priority: Execution priority (0=critical, 1=normal, 2=low).

        Returns:
            JSON with mission results, telemetry, and audit hash.
        """
        return await _execute_run(ctx, intent, budget_usd, delivery, context_hints, priority)

    @mcp.tool()
    async def cortex_run_async(
        intent: str,
        budget_usd: float = 0.10,
        timeout_s: float = 120.0,
        context_hints: str = "[]",
        priority: int = 1,
    ) -> str:
        """Execute a long-running sovereign mission via async pipeline.

        Unlike cortex_run, this uses the native async pipeline with proper
        timeout handling and cancellation support. Ideal for missions >30s.

        Args:
            intent: Natural language instruction for the mission.
            budget_usd: Maximum spend in USD (default: $0.10).
            timeout_s: Maximum execution time in seconds (default: 120).
            context_hints: JSON array of knowledge item IDs to prioritize.
            priority: Execution priority (0=critical, 1=normal, 2=low).

        Returns:
            JSON with mission results, telemetry, and audit hash.
        """
        return await _execute_run_async(ctx, intent, budget_usd, timeout_s, context_hints, priority)

    @mcp.tool()
    async def cortex_cancel(mission_id: str) -> str:
        """Cancel a running pipeline mission.

        Args:
            mission_id: The mission ID to cancel (from cortex_run output).

        Returns:
            JSON with cancellation status.
        """
        return await _execute_cancel(ctx, mission_id)

    @mcp.tool()
    async def cortex_pipeline_status() -> str:
        """Get the current pipeline status and recent mission telemetry.

        Returns:
            JSON with pipeline health, recent missions, and budget state.
        """
        return _get_status()

    @mcp.tool()
    async def cortex_pipeline_history(
        limit: int = 10,
    ) -> str:
        """Retrieve the pipeline audit ledger history.

        Args:
            limit: Maximum number of entries to return (default: 10).

        Returns:
            JSON array of ledger entries with mission IDs and hashes.
        """
        return _get_history(limit)
