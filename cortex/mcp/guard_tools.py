"""
Guard Daemon MCP Tools (α₁ Phase 3)

Exposes the Guard Daemon to external MCP agents, enabling them to:
1. Evaluate actions before executing them.
2. Check recent verdicts from the ledger.
3. Check daemon health.
"""

from typing import TYPE_CHECKING
import json

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from cortex.mcp.utils import _MCPContext

__all__ = ["register_guard_tools"]


def register_guard_tools(mcp: "FastMCP", ctx: "_MCPContext") -> None:
    """Register Guard Daemon tools on the MCP server."""

    @mcp.tool()
    async def cortex_guard_evaluate(action_type: str, target_path: str) -> str:
        """Evaluate an intended action against the CORTEX Guard policy before execution.

        Use this to check if a file modification or terminal command will trigger a BLOCK
        or WARN verdict from the security layer.

        Args:
            action_type: "file_write", "command_exec", or "dep_change"
            target_path: File path or command string
        """
        # In a fully integrated environment, this calls AgenticPolicyEngine directly.
        # For Phase 3 MVP, we perform a heuristic check matching the ActionClassifier logic.

        target = target_path.lower()

        if any(target.endswith(ext) for ext in [".env", ".pem", ".key"]):
            return "VERDICT: BLOCK\nReason: P0 Critical - Secret manipulation is forbidden."

        if any(cmd in target for cmd in ["rm -rf", "drop table"]):
            return "VERDICT: BLOCK\nReason: P0 Critical - Destructive command detected."

        if "requirements.txt" in target or "pyproject.toml" in target:
            return "VERDICT: WARN\nReason: P1 High - Dependency mutation detected. Proceed with caution."

        if "alembic" in target or "migrate" in target:
            return "VERDICT: WARN\nReason: P1 High - Migration detected."

        return "VERDICT: PASS\nReason: No policy violations detected."

    @mcp.tool()
    async def cortex_guard_verdicts(limit: int = 10) -> str:
        """List the most recent security verdicts emitted by the Guard Daemon."""
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT id, detail, timestamp FROM transactions "
                "WHERE action = 'GUARD_VERDICT' ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()

            if not rows:
                return "No recent security verdicts found in the immutable ledger."

            lines = ["Recent Guard Daemon Verdicts:"]
            for r in rows:
                tx_id, detail_json, ts = r
                try:
                    detail = json.loads(detail_json)
                    verdict = detail.get("verdict", "UNKNOWN")
                    target = detail.get("target", "N/A")
                    reason = detail.get("reason", "N/A")
                    lines.append(
                        f"[{ts}] Tx #{tx_id} | {verdict} | Target: {target} | Reason: {reason}"
                    )
                except json.JSONDecodeError:
                    lines.append(f"[{ts}] Tx #{tx_id} | Raw: {detail_json}")

            return "\n".join(lines)

    @mcp.tool()
    async def cortex_guard_status() -> str:
        """Get the current health and status of the Guard Daemon."""
        import os
        from pathlib import Path

        pid_file = Path.home() / ".cortex" / "guard.pid"
        if not pid_file.exists():
            return "Guard Daemon Status: OFFLINE (No PID file found)"

        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Test if process exists
            return f"Guard Daemon Status: ONLINE (PID: {pid})\nMonitoring: FileSystem + Shell"
        except (ValueError, OSError):
            return "Guard Daemon Status: OFFLINE (Stale PID file)"
