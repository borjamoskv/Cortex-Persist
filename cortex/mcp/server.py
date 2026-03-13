"""MCP Server Implementation.

Core logic for the CORTEX MCP Trust Server.
Provides memory, search, and EU AI Act compliance tools.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor

from cortex.engine import CortexEngine
from cortex.engine.ledger import ImmutableLedger
from cortex.immune.filters.base import Verdict
from cortex.immune.membrane import ImmuneMembrane
from cortex.mcp.guard import MCPGuard
from cortex.mcp.mega_tools import register_mega_tools
from cortex.mcp.trust_tools import register_trust_tools
from cortex.mcp.utils import (
    AsyncConnectionPool,
    MCPMetrics,
    MCPServerConfig,
    SimpleAsyncCache,
)

__all__ = ["create_mcp_server", "run_server"]

logger = logging.getLogger("cortex.mcp.server")

_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP

    _MCP_AVAILABLE = True
except ImportError:
    FastMCP = None  # type: ignore
    logger.debug("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")


# ─── Server Context ──────────────────────────────────────────────────


class _MCPContext:
    """Encapsulates the shared state for an MCP server instance.

    Replaces the old ``_state`` dict anti-pattern with a proper class
    that owns its lifecycle.
    """

    __slots__ = ("cfg", "metrics", "executor", "pool", "search_cache", "_initialized", "membrane")

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
            intent_payload, context_payload,
        )

        if triage.verdict != Verdict.PASS:
            ctx.metrics.record_error(is_immune_rejection=True)
            logger.warning(
                "Immune Membrane rejected store: %s",
                triage.risks_assumed,
            )
            return (
                f"❌ Rejected by Immune System "
                f"({triage.verdict.value}): "
                f"{triage.risks_assumed}"
            )

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
            "complexity_added": 1.0,     # Minimal entropy added by a read
            "complexity_removed": 0.0,
            "query_length": len(query),
        }
        
        # For search, we might want to flag highly adversarial-looking queries
        # even before the DB is hit.
        triage = await ctx.membrane.intercept(query, context)
        
        if triage.verdict == Verdict.BLOCK:
            ctx.metrics.record_error(is_immune_rejection=True)
            logger.warning(
                "MCP Immune System rejected search: %s\nRisks: %s", 
                query, triage.risks_assumed
            )
            return f"❌ Rejected by Immune System (Ω₃): {', '.join(triage.risks_assumed)}"
        elif triage.verdict == Verdict.HOLD:
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
        report = await ledger.verify_integrity_async()

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


# ─── Causal Episode Tracing (Epoch 8) ────────────────────────────────


def _register_trace_episode_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_trace_episode`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_trace_episode(
        query: str = "",
        fact_id: int = 0,
        project: str = "",
        limit: int = 3,
    ) -> str:
        """Trace causal episodes in CORTEX memory.

        Two modes:
        - If fact_id > 0: Trace the full causal DAG from that fact.
        - If query is provided: Find facts matching the query and
          reconstruct their causal episodes (why did X happen?).

        Returns the causal chain showing decision → consequence → fix.
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn

            if fact_id > 0:
                episode = await engine.trace_episode(fact_id)
                return (
                    f"Causal Episode from fact #{fact_id}:\n"
                    f"  Root: #{episode.root_fact_id}\n"
                    f"  Depth: {episode.depth}\n"
                    f"  Nodes: {len(episode.fact_chain)}\n"
                    f"  Entropy: {episode.entropy_density:.2f}\n"
                    f"  Project: {episode.project}\n\n"
                    f"{episode.summary}"
                )

            if query:
                episodes = await engine.recall_episode(
                    query, project, min(max(limit, 1), 10)
                )
                if not episodes:
                    return "No causal episodes found."

                lines = [f"Found {len(episodes)} causal episode(s):\n"]
                for ep in episodes:
                    lines.append(
                        f"--- Episode (root=#{ep.root_fact_id}, "
                        f"depth={ep.depth}, "
                        f"entropy={ep.entropy_density:.2f}) ---\n"
                        f"{ep.summary}\n"
                    )
                return "\n".join(lines)

            return "Provide either a query or a fact_id."


# ─── Causal Chain Traversal ──────────────────────────────────────────


def _register_trace_chain_tool(
    mcp: "FastMCP", ctx: _MCPContext,  # type: ignore[reportInvalidTypeForm]
) -> None:
    """Register the ``cortex_trace_chain`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_trace_chain(
        fact_id: int,
        direction: str = "down",
        max_depth: int = 10,
    ) -> str:
        """Traverse the causal chain from a fact.

        Args:
            fact_id: Starting fact ID.
            direction: 'up' (toward root) or 'down' (toward leaves).
            max_depth: Maximum recursion depth.

        Returns the causal DAG as a formatted chain.
        """
        await ctx.ensure_ready()

        if direction not in ("up", "down"):
            return "❌ direction must be 'up' or 'down'"

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(
                ctx.cfg.db_path, auto_embed=False,
            )
            engine._conn = conn
            chain = await engine.get_causal_chain(
                fact_id,
                direction=direction,
                max_depth=min(max(max_depth, 1), 50),
            )

        if not chain:
            return f"No causal chain from fact #{fact_id}."

        arrow = "↑" if direction == "up" else "↓"
        lines = [
            f"Causal Chain {arrow} from #{fact_id} "
            f"({len(chain)} nodes):\n",
        ]
        for f in chain:
            depth = f.get("causal_depth", "?")
            fid = f.get("id", "?")
            ftype = f.get("fact_type", "?")
            content = f.get("content", "")[:60]
            parent = f.get("parent_decision_id")
            parent_str = f"←#{parent}" if parent else "ROOT"
            lines.append(
                f"  [{depth}] #{fid} ({ftype}) "
                f"{parent_str}: {content}"
            )

        return "\n".join(lines)


# ─── Shannon Entropy Report (Epoch 13) ───────────────────────────────


def _register_shannon_report_tool(
    mcp: "FastMCP", ctx: _MCPContext,  # type: ignore[reportInvalidTypeForm]
) -> None:
    """Register the ``cortex_shannon_report`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_shannon_report(
        project: str = "",
    ) -> str:
        """Analyze Shannon entropy of CORTEX memory.

        Returns information-theoretic metrics: total entropy H(X),
        compression ratio, redundancy index, and per-type distribution.
        Useful for detecting knowledge bloat or semantic drift.
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn
            report = await engine.shannon_report(
                project or None,
            )

        lines = ["CORTEX Shannon Entropy Report:\n"]
        for key, value in report.items():
            if isinstance(value, float):
                lines.append(f"  {key}: {value:.4f}")
            elif isinstance(value, dict):
                lines.append(f"  {key}:")
                for k, v in value.items():
                    lines.append(f"    {k}: {v}")
            else:
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)


# ─── Session Handoff (Epoch 13) ──────────────────────────────────────


def _register_handoff_tool(
    mcp: "FastMCP", ctx: _MCPContext,  # type: ignore[reportInvalidTypeForm]
) -> None:
    """Register the ``cortex_handoff`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_handoff() -> str:
        """Generate a session handoff with hot decisions, causal episodes,
        active ghosts, and recent errors.

        This produces the context an incoming agent needs to resume work
        without loss of situational awareness.
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn

            from cortex.agents.handoff import generate_handoff
            handoff = await generate_handoff(engine)

        lines = [
            f"CORTEX Handoff v{handoff.get('version', '?')}:\n",
            f"  Generated: {handoff.get('generated_at', '?')}\n",
            f"  Active Projects: {', '.join(handoff.get('active_projects', []))}\n",
            f"\n  Hot Decisions ({len(handoff.get('hot_decisions', []))}):",
        ]
        for d in handoff.get("hot_decisions", [])[:5]:
            lines.append(f"    #{d['id']} [{d['project']}]: {d['content'][:80]}")

        episodes = handoff.get("causal_episodes", [])
        if episodes:
            lines.append(f"\n  Causal Episodes ({len(episodes)}):")
            for ep in episodes[:3]:
                lines.append(
                    f"    root=#{ep['root_fact_id']} "
                    f"depth={ep['depth']} entropy={ep['entropy']:.2f}"
                )

        ghosts = handoff.get("active_ghosts", [])
        if ghosts:
            lines.append(f"\n  Active Ghosts ({len(ghosts)}):")
            for g in ghosts[:5]:
                lines.append(f"    #{g['id']} [{g['project']}]: {g['reference']}")

        stats = handoff.get("stats", {})
        lines.append(
            f"\n  Stats: {stats.get('total_facts', 0)} facts, "
            f"{stats.get('total_projects', 0)} projects, "
            f"{stats.get('db_size_mb', 0):.1f} MB"
        )
        return "\n".join(lines)


# ─── Embedding Tools (Gemini Embedding 2) ────────────────────────────


def _register_embed_tool(
    mcp: "FastMCP", ctx: _MCPContext,  # type: ignore[reportInvalidTypeForm]
) -> None:
    """Register the ``cortex_embed`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_embed(
        text: str = "",
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> str:
        """Generate an embedding vector for text using the configured provider.

        Returns the embedding dimension and first 5 values as preview.
        When CORTEX_EMBEDDINGS=api and provider=gemini-v2, supports
        multimodal Matryoshka embeddings (768/1536/3072 dims).

        Args:
            text: Text to embed.
            task_type: Embedding task type (RETRIEVAL_DOCUMENT,
                RETRIEVAL_QUERY, SEMANTIC_SIMILARITY, CLASSIFICATION,
                CLUSTERING, CODE_RETRIEVAL_QUERY).
        """
        await ctx.ensure_ready()

        if not text.strip():
            return "❌ text cannot be empty"

        try:
            from cortex import config
            from cortex.embeddings.api_embedder import APIEmbedder

            if config.EMBEDDINGS_MODE != "api":
                return (
                    "❌ Embedding via MCP requires API mode. "
                    "Set CORTEX_EMBEDDINGS=api"
                )

            embedder = APIEmbedder(
                provider=config.EMBEDDINGS_PROVIDER,
                target_dimension=config.EMBEDDINGS_DIMENSION,
                task_type=task_type,
            )

            try:
                vector = await embedder.embed(text)
            finally:
                await embedder.close()

            preview = [f"{v:.4f}" for v in vector[:5]]
            return (
                f"✅ Embedding generated\n"
                f"  Provider: {config.EMBEDDINGS_PROVIDER}\n"
                f"  Dimension: {len(vector)}\n"
                f"  Task: {task_type}\n"
                f"  Preview: [{', '.join(preview)}, ...]"
            )
        except Exception as e:
            ctx.metrics.record_error()
            logger.error("Embedding failed: %s", e)
            return f"❌ Embedding failed: {e}"


def _register_embed_status_tool(
    mcp: "FastMCP", ctx: _MCPContext,  # type: ignore[reportInvalidTypeForm]
) -> None:
    """Register the ``cortex_embed_status`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_embed_status() -> str:
        """Show the current embedding provider configuration.

        Reports active provider, dimension, multimodal support,
        MRL capabilities, and all registered providers from presets.
        """
        try:
            from cortex import config
            from cortex.embeddings.api_embedder import get_provider_configs

            configs = get_provider_configs()
            active = config.EMBEDDINGS_PROVIDER

            lines = [
                "CORTEX Embedding Status:\n",
                f"  Mode: {config.EMBEDDINGS_MODE}",
                f"  Active Provider: {active}",
                f"  Target Dimension: {config.EMBEDDINGS_DIMENSION}",
                f"  Task Type: {config.EMBEDDINGS_TASK_TYPE}\n",
                f"  Registered Providers ({len(configs)}):",
            ]

            for name, cfg in configs.items():
                marker = "→ " if name == active else "  "
                mm = "🎨" if cfg.get("supports_multimodal") else "📝"
                mrl = "🪆" if cfg.get("supports_mrl") else ""
                dim = cfg.get("native_dimension", "?")
                lines.append(
                    f"  {marker}{mm}{mrl} {name}: "
                    f"dim={dim}"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error loading embed status: {e}"


# ─── Factory ─────────────────────────────────────────────────────────


def create_mcp_server(config: MCPServerConfig | None = None) -> "FastMCP":  # type: ignore[reportInvalidTypeForm]
    """Create and configure an optimized CORTEX MCP server instance.

    Each tool is registered via a dedicated helper, keeping this
    function focused on orchestration (cognitive complexity ≤ 5).
    """
    if not _MCP_AVAILABLE:
        raise ImportError("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")

    cfg = config or MCPServerConfig()
    mcp = FastMCP(  # type: ignore[reportOptionalCall]
        "CORTEX Trust Engine", host=cfg.host, port=cfg.port,
    )
    ctx = _MCPContext(cfg)

    # Core memory tools
    _register_store_tool(mcp, ctx)
    _register_search_tool(mcp, ctx)
    _register_status_tool(mcp, ctx)
    _register_ledger_tool(mcp, ctx)

    # Causal Episodic Trace (Epoch 8)
    _register_trace_episode_tool(mcp, ctx)

    # Causal Chain Traversal
    _register_trace_chain_tool(mcp, ctx)

    # Shannon Entropy & Session Handoff (Epoch 13)
    _register_shannon_report_tool(mcp, ctx)
    _register_handoff_tool(mcp, ctx)

    # Embedding Tools (Gemini Embedding 2)
    _register_embed_tool(mcp, ctx)
    _register_embed_status_tool(mcp, ctx)

    # Trust & Compliance tools (EU AI Act Art. 12)
    register_trust_tools(mcp, ctx)

    # Mega Poderosas (Aether, Void, Chronos paradigms)
    register_mega_tools(mcp, ctx)

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

    if cfg.transport == "sse":
        logger.info("Starting CORTEX MCP server v2 (SSE) on %s:%d", cfg.host, cfg.port)
        mcp.run(transport="sse")
    else:
        logger.info("Starting CORTEX MCP server v2 (stdio)")
        mcp.run()
