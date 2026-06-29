# [C5-REAL] Exergy-Maximized
"""MCP Server Implementation.

Core logic for the CORTEX MCP Trust Server.
Provides memory, search, and EU AI Act compliance tools.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from cortex.engine import CortexEngine
from cortex.extensions.immune.filters.base import Verdict
from cortex.extensions.immune.membrane import ImmuneMembrane
from cortex.integration.rustchain.mcp_tool import register_rustchain_tools
from cortex.ledger import ImmutableLedger
from cortex.mcp_server.apollo_tools import register_apollo_tools
from cortex.mcp_server.core_tools import (
    _register_embed_status_tool,
    _register_embed_tool,
)
from cortex.mcp_server.genesis_tools import register_genesis_tools
from cortex.mcp_server.guard import MCPGuard
from cortex.mcp_server.health_tools import register_health_tools
from cortex.mcp_server.kapso_tools import register_kapso_tools
from cortex.mcp_server.knowledge_watcher import start_knowledge_daemon
from cortex.mcp_server.mega_tools import register_mega_tools
from cortex.mcp_server.music_tools import register_music_tools
from cortex.mcp_server.singularity_tools import register_singularity_tools
from cortex.mcp_server.trust_tools import register_trust_tools
from cortex.mcp_server.utils import (
    AsyncConnectionPool,
    MCPMetrics,
    MCPServerConfig,
    SimpleAsyncCache,
)
from cortex.swarm import start_swarm_daemon

__all__ = ["create_mcp_server", "run_server"]

logger = logging.getLogger("cortex.mcp_server.server")

_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP as _FastMCP

    _MCP_AVAILABLE = True
    FastMCP = _FastMCP
except ImportError:
    FastMCP = None  # type: ignore
    logger.debug("MCP SDK not installed. Install with: pip install 'cortex-persist[mcp]'")


# ─── Server Context ──────────────────────────────────────────────────


class _MCPContext:
    """Encapsulates the shared state for an MCP server instance.

    Replaces the old ``_state`` dict anti-pattern with a proper class
    that owns its lifecycle.
    """

    __slots__ = ("_initialized", "cfg", "executor", "membrane", "metrics", "pool", "search_cache")

    def __init__(self, cfg: MCPServerConfig) -> None:
        self.cfg = cfg
        self.metrics = MCPMetrics()
        self.executor = ThreadPoolExecutor(max_workers=cfg.max_workers)
        self.pool = AsyncConnectionPool(cfg.db_path, max_connections=cfg.max_workers)
        self.search_cache = SimpleAsyncCache(maxsize=cfg.query_cache_size)
        self.membrane = ImmuneMembrane()
        self._initialized = False

    async def ensure_ready(self) -> None:
        if not self._initialized:
            await self.pool.initialize()
            self._initialized = True


# ─── Tool Registrators ───────────────────────────────────────────────


def _register_store_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_store`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_store(
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: str = "[]",
        source: str = "",
        parent_decision_id: int = 0,
    ) -> str:
        """Store a fact in CORTEX memory.

        Args:
            parent_decision_id: Causal link to parent fact (0 = auto-resolve).
        """
        await ctx.ensure_ready()

        try:
            parsed_tags = json.loads(tags) if tags else []
        except (json.JSONDecodeError, TypeError):
            parsed_tags = []

        try:
            MCPGuard.validate_store(project, content, fact_type, parsed_tags)
        except ValueError as e:
            ctx.metrics.record_error()
            logger.warning("MCP Guard rejected store: %s", e)
            return f"❌ Rejected by Guard: {e}"

        # Immune Membrane Interception (Ω₃ Byzantine Default)
        intent_payload = f"Store Fact [{fact_type}]: {content}"
        context_payload = {
            "project": project,
            "tags": parsed_tags,
            "source": source,
        }
        triage = await ctx.membrane.intercept(
            intent_payload,
            context_payload,
        )

        if triage.verdict != Verdict.PASS:
            ctx.metrics.record_error(is_immune_rejection=True)
            logger.warning(
                "Immune Membrane rejected store: %s",
                triage.risks_assumed,
            )
            return f"❌ Rejected by Immune System ({triage.verdict.value}): {triage.risks_assumed}"

        # Normalize parent_decision_id: 0 means None (auto-resolve)
        parent_id = parent_decision_id if parent_decision_id > 0 else None

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn

            fact_id = await engine.store(
                project,
                content,
                fact_type,
                parsed_tags,
                "stated",
                source or None,
                parent_decision_id=parent_id,
            )

        ctx.metrics.record_request()
        ctx.search_cache.clear()
        return f"✓ Stored fact #{fact_id} in project '{project}'"


def _register_search_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_search`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_search(
        query: str,
        project: str = "",
        top_k: int = 5,
    ) -> str:
        """Search CORTEX memory using semantic + text hybrid search."""
        await ctx.ensure_ready()

        try:
            MCPGuard.validate_search(query)
        except ValueError as e:
            ctx.metrics.record_error()
            logger.warning("MCP Guard rejected search: %s", e)
            return f"❌ Rejected by Guard: {e}"

        # 1. Immune Membrane Interception (Ω₃)
        context = {
            "source": "mcp_search",
            "project": project or "global",
            "is_external_source": True,  # MCP calls are effectively external
            "complexity_added": 1.0,  # Minimal entropy added by a read
            "complexity_removed": 0.0,
            "query_length": len(query),
        }

        # For search, we might want to flag highly adversarial-looking queries
        # even before the DB is hit.
        triage = await ctx.membrane.intercept(query, context)

        if triage.verdict == Verdict.BLOCK:
            ctx.metrics.record_error(is_immune_rejection=True)
            logger.warning(
                "MCP Immune System rejected search: %s\nRisks: %s", query, triage.risks_assumed
            )
            return f"❌ Rejected by Immune System (Ω₃): {', '.join(triage.risks_assumed)}"
        if triage.verdict == Verdict.HOLD:
            # We can allow HOLD for search, but log it
            logger.info("Search passed with HOLD warnings: %s", triage.risks_assumed)

        cache_key = f"{query}:{project}:{top_k}"
        cached_result = ctx.search_cache.get(cache_key)
        if cached_result:
            ctx.metrics.record_request(cached=True)
            return cached_result

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn

            results = await engine.search(
                query,
                project or None,  # type: ignore[reportArgumentType]
                min(max(top_k, 1), 20),  # type: ignore[reportArgumentType]
            )

        if not results:
            ctx.search_cache.set(cache_key, "No results found.")
            return "No results found."

        ctx.metrics.record_request()
        lines = [f"Found {len(results)} results:\n"]
        for r in results:
            lines.append(
                f"[#{r.fact_id}] (score: {r.score:.3f}) [{r.project}/{r.fact_type}]\n{r.content}\n"  # type: ignore[reportAttributeAccessIssue]
            )

        output = "\n".join(lines)
        ctx.search_cache.set(cache_key, output)
        return output


def _register_status_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_status`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_status() -> str:
        """Get CORTEX system status and metrics."""
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn
            stats = await engine.stats()

        m_summary = ctx.metrics.get_summary()
        return (
            f"CORTEX Status (Optimized v2):\n"
            f"  Facts: {stats.get('total_facts', 0)} total, "
            f"{stats.get('active_facts', 0)} active\n"
            f"  Projects: {stats.get('project_count', 0)}\n"
            f"  Fact Types: {json.dumps(stats.get('types', {}))}\n"
            f"  DB Size: {stats.get('db_size_mb', 0):.1f} MB\n"
            f"  MCP Metrics: {json.dumps(m_summary, indent=2)}"
        )


def _register_ledger_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_ledger_verify`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_ledger_verify() -> str:
        """Perform a full integrity check on the CORTEX ledger."""
        await ctx.ensure_ready()

        # ImmutableLedger expects a pool, not a single connection
        ledger = ImmutableLedger(ctx.pool)  # type: ignore[reportArgumentType]
        report = await ledger.audit_integrity_async()

        if report["valid"]:
            return (
                f"✅ Ledger Integrity: OK\n"
                f"Transactions verified: {report['tx_checked']}\n"
                f"Roots checked: {report['roots_checked']}"
            )
        return (
            f"❌ Ledger Integrity: VIOLATION\n"
            f"Violations: {json.dumps(report['violations'], indent=2)}"
        )


# ─── Factory ─────────────────────────────────────────────────────────


def create_mcp_server(config: MCPServerConfig | None = None) -> "FastMCP":  # type: ignore[reportInvalidTypeForm]
    """Create and configure an optimized CORTEX MCP server instance.

    Each tool is registered via a dedicated helper, keeping this
    function focused on orchestration (cognitive complexity ≤ 5).
    """
    if not _MCP_AVAILABLE:
        raise ImportError("MCP SDK not installed. Install with: pip install 'cortex-persist[mcp]'")

    cfg = config or MCPServerConfig()
    mcp = FastMCP(  # type: ignore[reportOptionalCall]
        "CORTEX Trust Engine",
        host=cfg.host,
        port=cfg.port,
    )
    ctx = _MCPContext(cfg)

    # Core memory tools
    _register_store_tool(mcp, ctx)
    _register_search_tool(mcp, ctx)
    _register_status_tool(mcp, ctx)
    # Embeddings are required for vector search
    _register_embed_tool(mcp, ctx)
    _register_embed_status_tool(mcp, ctx)

    # ─── Extended Toolset (Gated for Zero-Friction public release) ───
    if os.environ.get("CORTEX_MCP_FULL", "0") == "1":
        _register_ledger_tool(mcp, ctx)
        register_trust_tools(mcp, ctx)
        register_mega_tools(mcp, ctx)

        from cortex.mcp_server.hilbert_tools import register_hilbert_tools

        register_hilbert_tools(mcp, ctx)

        register_genesis_tools(mcp, ctx)
        register_health_tools(mcp, ctx)
        register_kapso_tools(mcp, ctx)
        register_music_tools(mcp)
        register_singularity_tools(mcp)
        register_rustchain_tools(mcp)

        from cortex.mcp_server.pipeline_tools import register_pipeline_tools

        register_pipeline_tools(mcp, ctx)

        register_apollo_tools(mcp)

    return mcp


# ─── Global Server Instance ──────────────────────────────────────────

# Default configuration
_default_config = MCPServerConfig()
mcp = create_mcp_server(_default_config)


def run_server(config: MCPServerConfig | None = None) -> None:
    """Start the CORTEX MCP server."""
    global mcp
    if config:
        mcp = create_mcp_server(config)

    cfg = config or _default_config

    if os.environ.get("CORTEX_MCP_FULL", "0") == "1":
        # V3 Singularity: Launch Live Knowledge Sync Daemon
        start_knowledge_daemon()
        # V4 Singularity: Launch Swarm Autopoiesis Engine
        start_swarm_daemon()

    if cfg.transport == "sse":
        logger.info("Starting CORTEX MCP server v2 (SSE) on %s:%d", cfg.host, cfg.port)
        mcp.run(transport="sse")
    else:
        logger.info("Starting CORTEX MCP server v2 (stdio)")
        mcp.run()
