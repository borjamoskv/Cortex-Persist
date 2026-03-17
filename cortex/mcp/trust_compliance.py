"""
CORTEX Trust Tools — Compliance Report & Decision Lineage.

Extracted from trust_tools.py to keep file size under 300 LOC.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from cortex.engine.ledger import ImmutableLedger

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from cortex.mcp.server import _MCPContext

__all__ = ["register_compliance_tools"]

logger = logging.getLogger("cortex.mcp.trust")


def register_compliance_tools(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register compliance report and decision lineage tools."""
    _register_compliance_report(mcp, ctx)
    _register_decision_lineage(mcp, ctx)


def _extract_agents_from_rows(agent_rows: list) -> set[str]:
    agents: set[str] = set()
    for row in agent_rows:
        if row[0]:
            for raw_tag in row[0].split(","):
                tag = raw_tag.strip()
                if tag.startswith("agent:"):
                    agents.add(tag)
    return agents


def _register_compliance_report(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register the ``cortex_compliance_report`` tool."""

    @mcp.tool()
    async def cortex_compliance_report() -> str:
        """Generate an EU AI Act Article 12 compliance snapshot.

        Produces a summary report covering:
        - Ledger integrity status (hash chain + Merkle checkpoints)
        - Decision logging completeness
        - Agent activity traceability
        - Data governance metrics

        This report can be used as evidence for regulatory audits.
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            # Total facts
            cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE deprecated_at IS NULL")
            total_facts = (await cursor.fetchone())[0]  # type: ignore[reportOptionalSubscript]

            # Decisions count
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM facts WHERE fact_type = 'decision' AND deprecated_at IS NULL"
            )
            decisions = (await cursor.fetchone())[0]  # type: ignore[reportOptionalSubscript]

            # Total transactions
            cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
            total_tx = (await cursor.fetchone())[0]  # type: ignore[reportOptionalSubscript]

            # Merkle checkpoints
            cursor = await conn.execute("SELECT COUNT(*) FROM merkle_roots")
            checkpoints = (await cursor.fetchone())[0]  # type: ignore[reportOptionalSubscript]

            # Projects
            cursor = await conn.execute(
                "SELECT COUNT(DISTINCT project) FROM facts WHERE deprecated_at IS NULL"
            )
            projects = (await cursor.fetchone())[0]  # type: ignore[reportOptionalSubscript]

            # Agents (from tags)
            cursor = await conn.execute(
                "SELECT DISTINCT tags FROM facts "
                "WHERE tags LIKE '%agent:%' AND deprecated_at IS NULL"
            )
            agent_rows = await cursor.fetchall()
            agents = _extract_agents_from_rows(agent_rows)  # type: ignore[reportArgumentType]

            # Oldest and newest fact
            cursor = await conn.execute(
                "SELECT MIN(created_at), MAX(created_at) FROM facts WHERE deprecated_at IS NULL"
            )
            time_range = await cursor.fetchone()

        # Verify ledger integrity
        ledger = ImmutableLedger(ctx.pool)  # type: ignore[reportArgumentType]
        integrity = await ledger.verify_integrity_async()

        now = datetime.now(timezone.utc).isoformat()

        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║   CORTEX — EU AI Act Compliance Report          ║",
            "║   Article 12: Record-Keeping Obligations         ║",
            "╚══════════════════════════════════════════════════╝",
            "",
            f"Report Generated: {now}",
            "",
            "── 1. Data Inventory ──",
            f"  Total Facts:           {total_facts}",
            f"  Logged Decisions:      {decisions}",
            f"  Active Projects:       {projects}",
            f"  Tracked Agents:        {len(agents)}",
            f"  Coverage Period:       {time_range[0] or 'N/A'} → {time_range[1] or 'N/A'}",  # type: ignore[reportOptionalSubscript]
            "",
            "── 2. Cryptographic Integrity ──",
            f"  Transaction Ledger:    {total_tx} entries",
            f"  Merkle Checkpoints:    {checkpoints}",
            f"  Hash Chain:            {'✅ VALID' if integrity['valid'] else '❌ BROKEN'}",
            f"  TX Verified:           {integrity.get('tx_checked', 0)}",
            f"  Roots Verified:        {integrity.get('roots_checked', 0)}",
        ]

        if not integrity["valid"]:
            lines.append(f"  ⚠️ Violations:        {len(integrity.get('violations', []))}")

        lines.extend(
            [
                "",
                "── 3. Compliance Checklist (Art. 12) ──",
                f"  [{'✅' if total_tx > 0 else '❌'}] Automatic logging of events (Art. 12.1)",
                f"  [{'✅' if decisions > 0 else '❌'}] Decision recording (Art. 12.2)",
                f"  [{'✅' if integrity['valid'] else '❌'}] Tamper-proof storage (Art. 12.3)",
                f"  [{'✅' if checkpoints > 0 else '❌'}] Periodic integrity verification (Art. 12.4)",
                f"  [{'✅' if len(agents) > 0 else '⚠️'}] Agent traceability (Art. 12.2d)",
                "",
                "── 4. Recommendation ──",
            ]
        )

        score = sum(
            [
                total_tx > 0,
                decisions > 0,
                integrity["valid"],
                checkpoints > 0,
                len(agents) > 0,
            ]
        )

        if score == 5:
            lines.append("  🟢 COMPLIANT — All Article 12 requirements met.")
        elif score >= 3:
            lines.append("  🟡 PARTIAL — Some requirements need attention.")
        else:
            lines.append("  🔴 NON-COMPLIANT — Critical gaps in record-keeping.")

        lines.append(f"\n  Compliance Score: {score}/5")

        return "\n".join(lines)


def _register_decision_lineage(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register the ``cortex_decision_lineage`` tool."""

    async def _find_target_fact(conn, fact_id: int, query: str, project: str):
        """Resolve the target fact by ID or search query."""
        if fact_id > 0:
            cursor = await conn.execute(
                "SELECT id, project, content, fact_type, created_at, tags "
                "FROM facts WHERE id = ? AND deprecated_at IS NULL",
                (fact_id,),
            )
            target = await cursor.fetchone()
            return target, f"❌ Fact #{fact_id} not found." if not target else None

        if query:
            conditions = ["deprecated_at IS NULL", "content LIKE ?"]
            params: list = [f"%{query}%"]
            if project:
                conditions.append("project = ?")
                params.append(project)
            where = " AND ".join(conditions)
            cursor = await conn.execute(
                f"SELECT id, project, content, fact_type, created_at, tags "  # nosec B608 — parameterized query
                f"FROM facts WHERE {where} "
                f"ORDER BY id DESC LIMIT 1",
                params,
            )
            target = await cursor.fetchone()
            return target, f"❌ No facts found matching '{query}'." if not target else None

        return None, "❌ Provide either fact_id or query."

    @mcp.tool()
    async def cortex_decision_lineage(
        fact_id: int = 0,
        query: str = "",
        project: str = "",
    ) -> str:
        """Trace the full lineage of a decision through the ledger.

        Given a fact ID or search query, reconstructs the chain of
        related decisions, showing how the agent arrived at this
        conclusion. Essential for AI explainability requirements.

        Args:
            fact_id: Specific fact ID to trace (0 = use query instead)
            query: Search for a decision by keyword (used if fact_id=0)
            project: Filter by project (optional)
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            target, error = await _find_target_fact(conn, fact_id, query, project)
            if error:
                return error

            tid, tproj, tcontent, ttype, tcreated, _ttags = target  # type: ignore[reportGeneralTypeIssues]

            # Find related decisions in the same project
            cursor = await conn.execute(
                "SELECT id, content, fact_type, created_at, tags "
                "FROM facts "
                "WHERE project = ? AND deprecated_at IS NULL "
                "AND created_at <= ? "
                "AND id != ? "
                "ORDER BY id DESC LIMIT 20",
                (tproj, tcreated, tid),
            )
            predecessors = await cursor.fetchall()

            # Find subsequent decisions
            cursor = await conn.execute(
                "SELECT id, content, fact_type, created_at, tags "
                "FROM facts "
                "WHERE project = ? AND deprecated_at IS NULL "
                "AND created_at > ? "
                "ORDER BY id ASC LIMIT 10",
                (tproj, tcreated),
            )
            successors = await cursor.fetchall()

        lines = [
            "═══ DECISION LINEAGE ═══",
            f"Target: #{tid} [{ttype}] in '{tproj}'",
            f"Content: {tcontent[:300]}",
            f"Created: {tcreated}",
            "",
        ]

        if predecessors:
            lines.append(f"── Preceding Context ({len(predecessors)} entries) ──")  # type: ignore[reportArgumentType]
            for p in reversed(predecessors[-10:]):  # type: ignore[reportIndexIssue]
                pid, pcontent, ptype, pcreated, _ptags = p
                lines.append(f"  [{pcreated}] #{pid} ({ptype}): {pcontent[:120]}")
            lines.append("")

        lines.append("  ──── ★ TARGET DECISION ────")
        lines.append(f"  [{tcreated}] #{tid} ({ttype}): {tcontent[:200]}")
        lines.append("")

        if successors:
            lines.append(f"── Subsequent Impact ({len(successors)} entries) ──")  # type: ignore[reportArgumentType]
            for s in successors[:5]:  # type: ignore[reportIndexIssue]
                sid, scontent, stype, screated, _stags = s
                lines.append(f"  [{screated}] #{sid} ({stype}): {scontent[:120]}")

        lines.extend(["", "═" * 40])
        return "\n".join(lines)
