"""Extended MCP tool registrations extracted from server.py (Seal 8 LOC compliance).

Contains: trace_episode, trace_chain, shannon_report, handoff, embed, embed_status.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex.engine import CortexEngine

if TYPE_CHECKING:
    from cortex.mcp.server import _MCPContext

logger = logging.getLogger("cortex.mcp.server")


def _register_trace_episode_tool(mcp, ctx: _MCPContext) -> None:
    """Register the ``cortex_trace_episode`` tool."""

    @mcp.tool()
    async def cortex_trace_episode(
        query: str = "", fact_id: int = 0, project: str = "", limit: int = 3,
    ) -> str:
        """Trace causal episodes in CORTEX memory."""
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


def _register_trace_chain_tool(mcp, ctx: _MCPContext) -> None:
    """Register the ``cortex_trace_chain`` tool."""

    @mcp.tool()
    async def cortex_trace_chain(
        fact_id: int, direction: str = "down", max_depth: int = 10,
    ) -> str:
        """Traverse the causal chain from a fact."""
        await ctx.ensure_ready()
        if direction not in ("up", "down"):
            return "❌ direction must be 'up' or 'down'"
        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn
            chain = await engine.get_causal_chain(
                fact_id, direction=direction, max_depth=min(max(max_depth, 1), 50),
            )
        if not chain:
            return f"No causal chain from fact #{fact_id}."
        arrow = "↑" if direction == "up" else "↓"
        lines = [f"Causal Chain {arrow} from #{fact_id} ({len(chain)} nodes):\n"]
        for f in chain:
            depth = f.get("causal_depth", "?")
            fid = f.get("id", "?")
            ftype = f.get("fact_type", "?")
            content = f.get("content", "")[:60]
            parent = f.get("parent_decision_id")
            parent_str = f"←#{parent}" if parent else "ROOT"
            lines.append(f"  [{depth}] #{fid} ({ftype}) {parent_str}: {content}")
        return "\n".join(lines)


def _register_shannon_report_tool(mcp, ctx: _MCPContext) -> None:
    """Register the ``cortex_shannon_report`` tool."""

    @mcp.tool()
    async def cortex_shannon_report(project: str = "") -> str:
        """Analyze Shannon entropy of CORTEX memory."""
        await ctx.ensure_ready()
        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn
            report = await engine.shannon_report(project or None)
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


def _register_handoff_tool(mcp, ctx: _MCPContext) -> None:
    """Register the ``cortex_handoff`` tool."""

    @mcp.tool()
    async def cortex_handoff() -> str:
        """Generate a session handoff with hot decisions and active ghosts."""
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


def _register_embed_tool(mcp, ctx: _MCPContext) -> None:
    """Register the ``cortex_embed`` tool."""

    @mcp.tool()
    async def cortex_embed(
        text: str = "", task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> str:
        """Generate an embedding vector for text."""
        await ctx.ensure_ready()
        if not text.strip():
            return "❌ text cannot be empty"
        try:
            from cortex import config
            from cortex.embeddings.api_embedder import APIEmbedder
            if config.EMBEDDINGS_MODE != "api":
                return "❌ Embedding via MCP requires API mode. Set CORTEX_EMBEDDINGS=api"
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
        except Exception as e:  # noqa: BLE001
            ctx.metrics.record_error()
            logger.error("Embedding failed: %s", e)
            return f"❌ Embedding failed: {e}"


def _register_embed_status_tool(mcp, ctx: _MCPContext) -> None:
    """Register the ``cortex_embed_status`` tool."""

    @mcp.tool()
    async def cortex_embed_status() -> str:
        """Show the current embedding provider configuration."""
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
                lines.append(f"  {marker}{mm}{mrl} {name}: dim={dim}")
            return "\n".join(lines)
        except Exception as e:  # noqa: BLE001
            return f"❌ Error loading embed status: {e}"
