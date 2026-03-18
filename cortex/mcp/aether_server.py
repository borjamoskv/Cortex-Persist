"""CORTEX MCP Server for Aether integration.

Sovereign bridge between local CORTEX infrastructure and the
Aether autonomous agent (Gemini 3 model). Exposes memory, file
reading over massive context windows, and Axiom 3 verified
execution.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None  # type: ignore

from cortex.config import DB_PATH
from cortex.mcp.utils import (
    AsyncConnectionPool,
    MCPMetrics,
    SimpleAsyncCache,
)

logger = logging.getLogger("cortex.mcp.aether")


class AetherContext:
    """State and lifecycle management for the Aether MCP server."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.metrics = MCPMetrics()
        self.pool = AsyncConnectionPool(self.db_path, max_connections=4)
        self.search_cache = SimpleAsyncCache(maxsize=100)
        self._initialized = False

    async def ensure_ready(self) -> None:
        if not self._initialized:
            await self.pool.initialize()
            self._initialized = True

    def engine_from_conn(self, conn: Any) -> Any:
        """Create a CortexEngine wired to a pooled connection."""
        from cortex.engine import CortexEngine

        engine = CortexEngine(self.db_path, auto_embed=False)
        engine._conn = conn  # noqa: SLF001
        return engine


def _axiom_3_verify(action_type: str, details: str) -> bool:
    """Enforce Axiom 3 (Byzantine Default): Verify before trust.

    Surfaces a macOS physical dialog asking the user to confirm
    a destructive action requested by the Aether agent.
    """
    logger.warning(
        "Axiom 3 Verification Triggered: %s - %s",
        action_type,
        details,
    )
    prompt = (
        f"Aether MCP Server is requesting a MUST-VERIFY action:"
        f"\\\\n\\\\n"
        f"Type: {action_type}\\\\n"
        f"Payload: {details[:200]}\\\\n\\\\n"
        f"Do you authorize this?"
    )

    script = f'''
    try
        set theDialogText to "{prompt}"
        display dialog theDialogText buttons {{"Deny", "Authorize"}} \
default button "Deny" \
with title "CORTEX Axiom 3 — Byzantine Verify" with icon caution
        if button returned of result is "Authorize" then
            return "true"
        else
            return "false"
        end if
    on error
        return "false"
    end try
    '''

    try:
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=300,  # Will auto-deny if timed out
        )
        return "true" in res.stdout.strip().lower()
    except subprocess.TimeoutExpired:
        logger.error("Axiom 3 Verification Timed out after 5 minutes.")
        return False
    except Exception as e:  # noqa: BLE001
        logger.error("Axiom 3 Verification OSAScript failed: %s", e)
        return False


def create_aether_server(
    db_path: str = DB_PATH,
    host: str = "127.0.0.1",
    port: int = 5001,
) -> FastMCP:  # type: ignore[reportInvalidTypeForm]
    """Create the Aether FastMCP server instance."""
    if FastMCP is None:
        raise ImportError("MCP SDK not installed. Run: pip install 'mcp'")

    mcp = FastMCP("MOSKV-Aether Sovereign Engine", host=host, port=port)
    ctx = AetherContext(db_path)

    @mcp.tool()
    async def cortex_search_memory(query: str, project: str = "", top_k: int = 20) -> str:
        """Search CORTEX local memory using vector embeddings."""
        await ctx.ensure_ready()

        cache_key = f"aether:{query}:{project}:{top_k}"
        cached_result = ctx.search_cache.get(cache_key)
        if cached_result:
            return cached_result

        async with ctx.pool.acquire() as conn:
            engine = ctx.engine_from_conn(conn)
            results = await engine.search(
                query,
                project or None,
                min(max(top_k, 5), 50),
            )

        if not results:
            return "No memory records found."

        ctx.metrics.record_request()

        output = [f"Found {len(results)} context chunks:"]
        for r in results:
            output.append(
                f"[FACT #{r.fact_id} | PROJECT: {r.project} "
                f"| TYPE: {r.fact_type} "
                f"| SCORE: {r.score:.3f}]\n"
                f"{r.content}\n---"
            )

        final_str = "\n".join(output)
        ctx.search_cache.set(cache_key, final_str)
        return final_str

    @mcp.tool()
    async def cortex_read_file(filepath: str, max_lines: int = 5000) -> str:
        """Read a massive system file. Tuned for Gemini 3's
        1M context window.

        Args:
            filepath: Absolute path to the file.
            max_lines: Max lines to return to avoid stalling the buffer. Max 50,000.
        """
        path = Path(filepath).resolve()
        if not path.exists() or not path.is_file():
            return f"❌ File not found: {filepath}"

        limit = min(abs(max_lines), 50000)

        def _read() -> str:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > limit:
                content = "".join(lines[:limit])
                return (
                    f"⚠️ Output truncated to first {limit} "
                    f"lines (total length was {len(lines)} lines).\n\n"
                    f"{content}"
                )
            return "".join(lines)

        try:
            return await asyncio.to_thread(_read)
        except UnicodeDecodeError:
            return f"❌ File {filepath} is binary or not UTF-8."
        except Exception as e:  # noqa: BLE001
            return f"❌ Error reading file: {e}"

    @mcp.tool()
    async def cortex_store_decision(project: str, decision: str) -> str:
        """Persist an architectural decision or ghost directly
        to the local CORTEX DB.

        Requires physical user verification (Axiom 3).
        """
        await ctx.ensure_ready()

        # Axiom 3 verification loop
        if not _axiom_3_verify(
            "Database Write (Decision)",
            f"[{project}] {decision}",
        ):
            return "❌ Operation aborted: Axiom 3 user physical authorization DENIED."

        async with ctx.pool.acquire() as conn:
            engine = ctx.engine_from_conn(conn)
            fact_id = await engine.store(
                project,
                decision,
                "decision",
                ["mcp-aether"],
                "stated",
                "agent:gemini:aether",
            )

        ctx.search_cache.clear()
        ctx.metrics.record_request()
        return f"✅ Verified and Stored decision #{fact_id} in project '{project}'"

    @mcp.tool()
    async def cortex_execute_bash(command: str, cwd: str = ".") -> str:
        """Execute a bash command on the host macOS machine.

        WARNING: Highly destructive. Will trigger an immediate OS-level authorization
        prompt (Axiom 3 validation). Ensure the command is 100% accurate.
        """
        if not _axiom_3_verify("Shell Execution", f"cd {cwd} && {command}"):
            return "❌ Shell execution aborted: Axiom 3 user physical authorization DENIED."

        logger.warning("Executing authorized bash command: %s", command)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode().strip()
            err_output = stderr.decode().strip()

            res = f"Exit code: {process.returncode}\n"
            if output:
                res += f"STDOUT:\n{output}\n"
            if err_output:
                res += f"STDERR:\n{err_output}\n"

            return res
        except Exception as e:  # noqa: BLE001
            return f"❌ Subprocess error: {e}"

    return mcp


def run_aether_mcp(
    host: str = "127.0.0.1",
    port: int = 5001,
    transport: str = "sse",
) -> None:
    """Boot the Aether CORTEX MCP Server."""
    server = create_aether_server(host=host, port=port)
    if transport == "sse":
        logger.info(
            "Starting CORTEX Aether MCP server on %s:%d (SSE Transport)",
            host,
            port,
        )
        server.run(transport="sse")
    else:
        logger.info("Starting CORTEX Aether MCP server (STDIO Transport)")
        server.run()
