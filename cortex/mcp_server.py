"""
CORTEX v4.0 — MCP Server.

Model Context Protocol server exposing CORTEX as tools for any AI agent.
Uses FastMCP (mcp Python SDK) for stdio transport.
"""

from __future__ import annotations

import atexit
import json
import logging
from typing import Optional

logger = logging.getLogger("cortex.mcp")

__all__ = ["create_mcp_server", "run_server"]

# ─── Server Setup ─────────────────────────────────────────────────────

_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    FastMCP = None  # type: ignore
    logger.debug("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")


def create_mcp_server(db_path: str = "~/.cortex/cortex.db") -> "FastMCP":
    """Create and configure a CORTEX MCP server instance.

    Args:
        db_path: Path to CORTEX database.

    Returns:
        Configured FastMCP server ready to run.

    Raises:
        ImportError: If MCP SDK is not installed.
    """
    if not _MCP_AVAILABLE:
        raise ImportError(
            "MCP SDK not installed. Install with: pip install mcp\n"
            "Or: pip install 'cortex-memory[mcp]'"
        )

    from cortex.engine import CortexEngine

    mcp = FastMCP(
        "CORTEX Memory",
        description="Sovereign memory infrastructure for AI agents. "
        "Store, search, and recall facts with semantic search and temporal queries.",
    )

    # Lazy engine initialization
    _engine: dict = {}

    def get_engine() -> CortexEngine:
        if "instance" not in _engine:
            eng = CortexEngine(db_path=db_path)
            eng.init_db()
            _engine["instance"] = eng
            atexit.register(eng.close)
        return _engine["instance"]

    # ─── Tools ────────────────────────────────────────────────────

    @mcp.tool()
    def cortex_store(
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: str = "[]",
        source: str = "",
    ) -> str:
        """Store a fact in CORTEX memory.

        Args:
            project: Project/namespace for the fact (e.g., 'myproject').
            content: The fact content to store.
            fact_type: Type: knowledge, decision, mistake, bridge, ghost.
            tags: JSON array of tags, e.g. '["important", "bug"]'.
            source: Where this fact came from.

        Returns:
            Confirmation with the fact ID.
        """
        engine = get_engine()
        try:
            parsed_tags = json.loads(tags) if tags else []
        except json.JSONDecodeError:
            parsed_tags = []

        fact_id = engine.store(
            project=project,
            content=content,
            fact_type=fact_type,
            tags=parsed_tags,
            source=source or None,
        )
        return f"✓ Stored fact #{fact_id} in project '{project}'"

    @mcp.tool()
    def cortex_search(
        query: str,
        project: str = "",
        top_k: int = 5,
    ) -> str:
        """Search CORTEX memory using semantic + text hybrid search.

        Args:
            query: Natural language search query.
            project: Optional project filter.
            top_k: Number of results (1-20).

        Returns:
            Formatted search results with scores.
        """
        engine = get_engine()
        results = engine.search(
            query=query,
            project=project or None,
            top_k=min(max(top_k, 1), 20),
        )

        if not results:
            return "No results found."

        lines = [f"Found {len(results)} results:\n"]
        for r in results:
            lines.append(
                f"[#{r.fact_id}] (score: {r.score:.3f}) "
                f"[{r.project}/{r.fact_type}]\n{r.content}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    def cortex_recall(
        project: str,
        limit: int = 20,
    ) -> str:
        """Load all active facts for a project.

        Args:
            project: Project to recall facts from.
            limit: Maximum facts to return.

        Returns:
            Formatted list of project facts.
        """
        engine = get_engine()
        facts = engine.recall(project=project, limit=limit)

        if not facts:
            return f"No facts found for project '{project}'."

        lines = [f"📁 {project} — {len(facts)} facts:\n"]
        for f in facts:
            try:
                tags = f.tags if isinstance(f.tags, list) else json.loads(f.tags) if isinstance(f.tags, str) else []
            except (json.JSONDecodeError, TypeError):
                tags = []
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"  #{f.id} [{f.fact_type}]{tag_str}: {f.content[:200]}")
        return "\n".join(lines)

    @mcp.tool()
    def cortex_graph(
        project: str = "",
        limit: int = 30,
    ) -> str:
        """Show the entity-relationship knowledge graph.

        Args:
            project: Optional project filter.
            limit: Max entities to show.

        Returns:
            Formatted entity graph with relationships.
        """
        engine = get_engine()
        data = engine.graph(project=project or None, limit=limit)

        if not data["entities"]:
            return "No entities in the knowledge graph yet."

        lines = [f"🧠 Knowledge Graph ({data['stats']['total_entities']} entities, "
                 f"{data['stats']['total_relationships']} relationships):\n"]

        for ent in data["entities"]:
            lines.append(f"  • {ent['name']} ({ent['type']}) — {ent['mentions']} mentions")

        if data["relationships"]:
            lines.append("\nRelationships:")
            id_to_name = {e["id"]: e["name"] for e in data["entities"]}
            for rel in sorted(data["relationships"], key=lambda r: -r["weight"])[:10]:
                src = id_to_name.get(rel["source"], f"#{rel['source']}")
                tgt = id_to_name.get(rel["target"], f"#{rel['target']}")
                lines.append(f"  {src} ──[{rel['type']}]── {tgt} (w={rel['weight']:.1f})")

        return "\n".join(lines)

    @mcp.tool()
    def cortex_status() -> str:
        """Get CORTEX system status and statistics.

        Returns:
            System health and statistics summary.
        """
        engine = get_engine()
        stats = engine.stats()
        return (
            f"CORTEX Status:\n"
            f"  Facts: {stats.get('total_facts', 0)} total, "
            f"{stats.get('active_facts', 0)} active\n"
            f"  Projects: {stats.get('projects', 0)}\n"
            f"  Embeddings: {stats.get('embeddings', 0)}\n"
            f"  DB Size: {stats.get('db_size_mb', 0):.1f} MB"
        )

    # ─── Resources ────────────────────────────────────────────────

    @mcp.resource("cortex://projects")
    def list_projects() -> str:
        """List all projects in CORTEX memory."""
        engine = get_engine()
        conn = engine.get_connection()
        rows = conn.execute(
            "SELECT DISTINCT project FROM facts WHERE valid_until IS NULL "
            "ORDER BY project"
        ).fetchall()
        projects = [r[0] for r in rows]
        return json.dumps({"projects": projects, "count": len(projects)})

    @mcp.resource("cortex://stats")
    def memory_stats() -> str:
        """Get CORTEX memory statistics."""
        engine = get_engine()
        stats = engine.stats()
        return json.dumps(stats)

    return mcp


def run_server(db_path: str = "~/.cortex/cortex.db") -> None:
    """Start the CORTEX MCP server (stdio transport)."""
    mcp = create_mcp_server(db_path)
    logger.info("Starting CORTEX MCP server (stdio transport)...")
    mcp.run()
