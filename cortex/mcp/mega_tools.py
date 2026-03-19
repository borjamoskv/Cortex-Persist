"""
CORTEX Mega Poderosas Tools — High-Power Architectural MCP Extensions.

Production implementation with real data from:
- EntropyAnnihilator (AST-based file analysis)
- CORTEX DB (facts, transactions, ghosts, bridges)
- Filesystem scanning
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cortex.mcp.decorators import with_db

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from cortex.mcp.server import _MCPContext

__all__ = ["register_mega_tools"]

logger = logging.getLogger("cortex.mcp.mega")

# Safe base directories for entropy scanning
# Include resolved tempdir for macOS (/var/folders/... symlinked from /tmp)
_SAFE_BASES = (
    str(Path.home()),
    "/tmp",
    "/private/tmp",
    str(Path(tempfile.gettempdir()).resolve()),
)


def register_mega_tools(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register all 'Mega Poderosas' tools on the MCP server."""
    _register_reality_weaver(mcp, ctx)
    _register_entropy_cracker(mcp, ctx)
    _register_temporal_nexus(mcp, ctx)


# ─── Reality Weaver ──────────────────────────────────────────────────


def _register_reality_weaver(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register the ``cortex_reality_weaver`` tool."""

    @mcp.tool()
    @with_db(ctx)
    async def cortex_reality_weaver(conn: Any, intent: str, project: str = "custom") -> str:
        """Orchestrate the creation of system structures from a high-level intent.

        Queries CORTEX memory for existing decisions, bridges, and ghosts
        related to the project, then generates an architectural plan
        grounded in real data.

        Args:
            intent: High-level description of what to build
            project: Project namespace to query
        """
        lines = [f"═══ REALITY WEAVING: {intent.upper()} ═══", ""]

        # 1. Query existing facts for this project
        # Fact distribution by type
        cursor = await conn.execute(
            """
            SELECT fact_type, count(*) as cnt
            FROM facts
            WHERE (project = ? OR ? = '')
              AND is_tombstoned = 0
            GROUP BY fact_type
            ORDER BY cnt DESC
            """,
            (project, project),
        )
        type_rows = await cursor.fetchall()

        # Recent decisions (last 30 days)
        cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        cursor = await conn.execute(
            """
            SELECT content FROM facts
            WHERE project = ? AND fact_type = 'decision'
              AND is_tombstoned = 0 AND created_at > ?
            ORDER BY id DESC LIMIT 5
            """,
            (project, cutoff_30d),
        )
        decisions = list(await cursor.fetchall())

        # Active ghosts (unfinished work)
        cursor = await conn.execute(
            """
            SELECT content FROM facts
            WHERE project = ? AND fact_type = 'ghost'
              AND is_tombstoned = 0
            ORDER BY id DESC LIMIT 5
            """,
            (project,),
        )
        ghosts = list(await cursor.fetchall())

        # Bridges (cross-project patterns)
        cursor = await conn.execute(
            """
            SELECT content FROM facts
            WHERE project = ? AND fact_type = 'bridge'
              AND is_tombstoned = 0
            ORDER BY id DESC LIMIT 3
            """,
            (project,),
        )
        bridges = list(await cursor.fetchall())

        # 2. Build report from real data
        if type_rows:
            lines.append("### Knowledge Base")
            lines.append("")
            lines.append("| Fact Type | Count |")
            lines.append("| :--- | ---: |")
            total = 0
            for ftype, cnt in type_rows:
                lines.append(f"| {ftype} | {cnt} |")
                total += cnt
            lines.append(f"| **TOTAL** | **{total}** |")
            lines.append("")
        else:
            lines.append(f"> No facts found for project '{project}'. Virgin territory.")
            lines.append("")

        if decisions:
            lines.append("### Recent Decisions")
            lines.append("")
            for (content,) in decisions:
                lines.append(f"- {content[:120]}")
            lines.append("")

        if ghosts:
            lines.append("### ⚠️ Active Ghosts (Unfinished Work)")
            lines.append("")
            for (content,) in ghosts:
                lines.append(f"- 👻 {content[:120]}")
            lines.append("")

        if bridges:
            lines.append("### 🌉 Cross-Project Bridges")
            lines.append("")
            for (content,) in bridges:
                lines.append(f"- {content[:120]}")
            lines.append("")

        # 3. Architectural recommendation
        lines.append("### Proposed Structure")
        lines.append("")
        lines.append("| Path | Type | Purpose | Priority |")
        lines.append("| :--- | :--- | :--- | :--- |")
        lines.append(f"| `{project}/core/` | [DIR] | Orchestration Layer | HIGH |")
        lines.append(f"| `{project}/api/` | [DIR] | External Interface | HIGH |")

        if ghosts:
            lines.append(
                f"| `{project}/debt/` | [DIR] | "
                f"Ghost Resolution ({len(ghosts)} pending) | CRITICAL |"
            )
        if bridges:
            lines.append(
                f"| `{project}/bridges/` | [DIR] | "
                f"Bridge Integration ({len(bridges)} active) | MEDIUM |"
            )

        lines.append(f"| `{project}/README.md` | [FILE] | Reality Manifest | HIGH |")
        lines.append("")

        ghost_warning = f" ⚠️ {len(ghosts)} ghost(s) need resolution first." if ghosts else ""
        lines.append(
            f"> [!IMPORTANT]\n"
            f"> Reality Weaver grounded this intent in "
            f"{total if type_rows else 0} existing facts.{ghost_warning}"
        )

        ctx.metrics.record_request()
        return "\n".join(lines)


# ─── Entropy Cracker ─────────────────────────────────────────────────


def _resolve_safe_path(path: str) -> str | None:
    """Resolve path safely, rejecting traversal outside safe bases."""
    resolved = str(Path(path).expanduser().resolve())
    if any(resolved.startswith(base) for base in _SAFE_BASES):
        return resolved
    return None


def _register_entropy_cracker(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register the ``cortex_entropy_cracker`` tool."""

    @mcp.tool()
    async def cortex_entropy_cracker(path: str) -> str:
        """Analyze codebase for redundancy, dead code, and complexity.

        Uses the EntropyAnnihilator engine (AST-based Landauer analysis)
        to calculate real thermodynamic entropy per file.

        Args:
            path: Directory to analyze (relative to home or absolute)
        """
        await ctx.ensure_ready()

        safe_path = _resolve_safe_path(path)
        if safe_path is None:
            ctx.metrics.record_error()
            return f"❌ Path '{path}' is outside allowed boundaries."

        if not os.path.isdir(safe_path):
            ctx.metrics.record_error()
            return f"❌ Path '{safe_path}' is not a valid directory."

        # Use the real EntropyAnnihilator
        from cortex.engine.entropy import EntropyAnnihilator

        annihilator = EntropyAnnihilator(safe_path)
        scan_results = annihilator.scan_ecosystem()

        if not scan_results:
            ctx.metrics.record_request()
            return (
                f"═══ ENTROPY CRACKER: {path} ═══\n"
                "No Python files found for analysis.\n"
                "Entropy Level: N/A"
            )

        # Calculate real metrics
        entropies = [e for _, e in scan_results]
        total_files = len(entropies)
        max_entropy = max(entropies)
        mean_entropy = sum(entropies) / total_files
        # Density = inverse of entropy (high entropy = low density)
        max_expected = max(max_entropy, 500.0)  # normalize
        density_score = max(0, min(100, int(100 - (mean_entropy / max_expected * 100))))

        # Classify
        if density_score < 40:
            level = "CRITICAL"
        elif density_score > 80:
            level = "STABLE"
        else:
            level = "MEDIUM"

        lines = [
            f"═══ ENTROPY CRACKER ANALYSIS: {path} ═══",
            f"Files Scanned: {total_files}",
            f"Density Score: {density_score}/100",
            f"Entropy Level: {level}",
            f"Mean Entropy:  {mean_entropy:.1f}",
            f"Max Entropy:   {max_entropy:.1f}",
            "",
        ]

        # Top energy sinks
        top_sinks = scan_results[:10]
        if top_sinks:
            lines.append("### Top Energy Sinks")
            lines.append("")
            lines.append("| File | Entropy | Verdict |")
            lines.append("| :--- | ---: | :--- |")
            for filepath, entropy in top_sinks:
                rel = os.path.relpath(filepath, safe_path)
                verdict = (
                    "🔴 PURGE" if entropy > 200 else "🟡 REFACTOR" if entropy > 50 else "🟢 OK"
                )
                lines.append(f"| `{rel}` | {entropy:.1f} | {verdict} |")
            lines.append("")

        # Purgeable sinks
        sinks = annihilator.purge_energy_sinks(threshold=100.0)
        if sinks:
            lines.append(
                f"═══ VERDICT: {len(sinks)} file(s) exceed entropy threshold. "
                f"MEJORAlo --brutal recommended. ═══"
            )
        else:
            lines.append("═══ VERDICT: Entropy within acceptable bounds. ═══")

        ctx.metrics.record_request()
        return "\n".join(lines)


# ─── Temporal Nexus ──────────────────────────────────────────────────


def _register_temporal_nexus(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register the ``cortex_temporal_nexus`` tool."""

    @mcp.tool()
    @with_db(ctx)
    async def cortex_temporal_nexus(conn: Any, project: str = "") -> str:
        """Analyze technical debt drift and project evolution over time.

        Queries the CORTEX ledger for real mutation history, ghost density,
        temporal drift, bridge activity, and error rates.

        Args:
            project: Project to analyze (empty = global)
        """
        now = datetime.now(timezone.utc)
        cutoff_7d = (now - timedelta(days=7)).isoformat()
        cutoff_14d = (now - timedelta(days=14)).isoformat()

        # 1. Transaction history (ledger)
        try:
            cursor = await conn.execute(
                """
                SELECT count(*) as tx_count,
                       min(timestamp) as start_date,
                       max(timestamp) as last_date
                FROM transactions
                WHERE project = ? OR ? = ''
                """,
                (project, project),
            )
            tx_stats = await cursor.fetchone()
        except Exception:  # noqa: BLE001 — fallback if stats query fails
            tx_stats = (0, "N/A", "N/A")

        # 2-6. Batched fact aggregates in one query
        cursor = await conn.execute(
            """
            SELECT
              SUM(CASE WHEN fact_type = 'ghost'
                AND is_tombstoned = 0
                THEN 1 ELSE 0 END),
              SUM(CASE WHEN is_tombstoned = 0
                THEN 1 ELSE 0 END),
              SUM(CASE WHEN fact_type = 'decision'
                AND is_tombstoned = 0
                AND created_at > ?
                THEN 1 ELSE 0 END),
              SUM(CASE WHEN fact_type = 'decision'
                AND is_tombstoned = 0
                AND created_at > ?
                AND created_at <= ?
                THEN 1 ELSE 0 END),
              SUM(CASE WHEN fact_type = 'bridge'
                AND is_tombstoned = 0
                THEN 1 ELSE 0 END),
              SUM(CASE WHEN fact_type = 'error'
                AND is_tombstoned = 0
                AND created_at > ?
                THEN 1 ELSE 0 END)
            FROM facts
            WHERE (project = ? OR ? = '')
            """,
            (
                cutoff_7d,
                cutoff_14d,
                cutoff_7d,
                cutoff_7d,
                project,
                project,
            ),
        )
        row = await cursor.fetchone()
        if row:
            ghost_count = row[0] or 0
            total_facts = row[1] or 0
            recent_decisions = row[2] or 0
            prev_decisions = row[3] or 0
            bridge_count = row[4] or 0
            recent_errors = row[5] or 0
        else:
            ghost_count = total_facts = 0
            recent_decisions = prev_decisions = 0
            bridge_count = recent_errors = 0

        # Calculate real metrics
        tx_count, start, last = tx_stats if tx_stats else (0, "N/A", "N/A")
        ghost_density = (ghost_count / max(total_facts, 1)) * 100
        drift = ((recent_decisions - prev_decisions) / max(prev_decisions, 1)) * 100

        # Classify ghost density
        if ghost_density > 20:
            ghost_level = "🔴 CRITICAL"
        elif ghost_density > 10:
            ghost_level = "🟡 ELEVATED"
        elif ghost_density > 5:
            ghost_level = "🟢 MODERATE"
        else:
            ghost_level = "🟢 LOW"

        # Classify drift direction
        if drift > 20:
            drift_label = f"+{drift:.1f}% (Accelerating)"
        elif drift < -20:
            drift_label = f"{drift:.1f}% (Decelerating)"
        else:
            drift_label = f"{drift:+.1f}% (Stable)"

        label = project or "GLOBAL"
        lines = [
            f"═══ TEMPORAL NEXUS: {label} ═══",
            "",
            "### Ledger",
            f"Total Mutations:  {tx_count}",
            f"First Pulse:      {start}",
            f"Last Evolution:   {last}",
            "",
            "### Vitals",
            f"Active Facts:     {total_facts}",
            f"Active Ghosts:    {ghost_count}",
            f"Ghost Density:    {ghost_density:.1f}% — {ghost_level}",
            f"Active Bridges:   {bridge_count}",
            f"Recent Errors:    {recent_errors} (7d)",
            "",
            "### Temporal Drift",
            f"Decisions (7d):   {recent_decisions}",
            f"Decisions (prev): {prev_decisions}",
            f"Drift:            {drift_label}",
            "",
        ]

        # Recommendations
        recs: list[str] = []
        if ghost_density > 15:
            recs.append("- 👻 Ghost density critical. Run `/ghost-control` to triage.")
        if recent_errors > 5:
            recs.append("- 🔴 High error rate. Investigate with `cortex search type:error`.")
        if drift < -30:
            recs.append("- 📉 Decision velocity dropping. Team may be blocked.")
        if bridge_count == 0:
            recs.append("- 🌉 No bridges detected. Cross-project learning stalled.")

        if recs:
            lines.append("### Recommendations")
            lines.append("")
            lines.extend(recs)
            lines.append("")

        # Summary note
        if ghost_density < 10 and recent_errors < 3:
            lines.append("> [!NOTE]")
            lines.append("> System evolving toward higher purity. No temporal paradoxes detected.")
        elif ghost_density > 20:
            lines.append("> [!WARNING]")
            lines.append(f"> Ghost accumulation detected ({ghost_count} active). Entropy rising.")
        else:
            lines.append("> [!NOTE]")
            lines.append(f"> System health: moderate. {ghost_count} ghost(s) pending resolution.")

        ctx.metrics.record_request()
        return "\n".join(lines)
