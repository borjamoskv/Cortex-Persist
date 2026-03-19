"""
CORTEX Trust Tools — Compliance Report & Decision Lineage.

Extracted from trust_tools.py to keep file size under 300 LOC.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from cortex.compliance.evaluator import ComplianceEvaluator
from cortex.mcp.decorators import with_db

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
    @with_db(ctx)
    async def cortex_compliance_report(conn: Any) -> str:
        """Generate an EU AI Act Article 12 compliance snapshot.

        Produces a summary report covering:
        - Ledger integrity status (hash chain + Merkle checkpoints)
        - Decision logging completeness
        - Agent activity traceability
        - Data governance metrics

        This report can be used as evidence for regulatory audits.
        """
        cursor = await conn.execute(
            "SELECT"
            "  SUM(CASE WHEN is_tombstoned = 0 THEN 1 ELSE 0 END),"
            "  SUM(CASE WHEN fact_type = 'decision' AND is_tombstoned = 0 THEN 1 ELSE 0 END),"
            "  COUNT(DISTINCT CASE WHEN is_tombstoned = 0 THEN project END),"
            "  MIN(CASE WHEN is_tombstoned = 0 THEN created_at END),"
            "  MAX(CASE WHEN is_tombstoned = 0 THEN created_at END)"
            " FROM facts"
        )
        row = await cursor.fetchone()
        if row:
            total_facts = row[0] or 0
            decisions = row[1] or 0
            projects = row[2] or 0
            time_range = (row[3], row[4])
        else:
            total_facts = decisions = projects = 0
            time_range = (None, None)

        # Transactions count
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
        total_tx = (await cursor.fetchone())[0]  # type: ignore[reportOptionalSubscript]

        # Merkle checkpoints
        cursor = await conn.execute("SELECT COUNT(*) FROM merkle_roots")
        checkpoints = (await cursor.fetchone())[0]  # type: ignore[reportOptionalSubscript]

        # Agents (from tags)
        cursor = await conn.execute(
            "SELECT DISTINCT tags FROM facts WHERE tags LIKE '%agent:%' AND is_tombstoned = 0"
        )
        agent_rows = await cursor.fetchall()
        agents = _extract_agents_from_rows(agent_rows)  # type: ignore[reportArgumentType]
        integrity = await ctx.ledger.verify_integrity_async()

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

        facts_summary = {
            "total_facts": total_facts,
            "sources": list(agents),
            "date_range": {
                "earliest": time_range[0],
                "latest": time_range[1],
            }
            if time_range[0] is not None
            else {},
        }

        checks = ComplianceEvaluator.evaluate(integrity, facts_summary)

        c1 = checks["art_12_1_automatic_logging"]["compliant"]
        c2 = checks["art_12_2_log_content"]["compliant"]
        c3 = checks["art_12_3_tamper_proof"]["compliant"]
        c4 = checks["art_12_4_periodic_verification"]["compliant"]
        c2d = checks["art_12_2d_agent_traceability"]["compliant"]

        lines.extend(
            [
                "",
                "── 3. Compliance Checklist (Art. 12) ──",
                f"  [{'✅' if c1 else '❌'}] Automatic logging of events (Art. 12.1)",
                f"  [{'✅' if c2 else '❌'}] Decision recording (Art. 12.2)",
                f"  [{'✅' if c3 else '❌'}] Tamper-proof storage (Art. 12.3)",
                f"  [{'✅' if c4 else '❌'}] Periodic integrity verification (Art. 12.4)",
                f"  [{'✅' if c2d else '⚠️'}] Agent traceability (Art. 12.2d)",
                "",
                "── 4. Recommendation ──",
            ]
        )

        score = ComplianceEvaluator.calculate_score(checks)

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
                "FROM facts WHERE id = ? AND is_tombstoned = 0",
                (fact_id,),
            )
            target = await cursor.fetchone()
            return target, f"❌ Fact #{fact_id} not found." if not target else None

        if query:
            conditions = ["is_tombstoned = 0", "content LIKE ?"]
            params: list = [f"%{query}%"]
            if project:
                conditions.append("project = ?")
                params.append(project)
            where = " AND ".join(conditions)
            cursor = await conn.execute(
                "SELECT id, project, content, "
                "fact_type, created_at, tags "  # nosec B608
                f"FROM facts WHERE {where} "
                f"ORDER BY id DESC LIMIT 1",
                params,
            )
            target = await cursor.fetchone()
            return target, f"❌ No facts found matching '{query}'." if not target else None

        return None, "❌ Provide either fact_id or query."

    @mcp.tool()
    @with_db(ctx)
    async def cortex_decision_lineage(
        conn: Any,
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
        target, error = await _find_target_fact(conn, fact_id, query, project)
        if error:
            return error

        (tid, tproj, tcontent, ttype, tcreated, _ttags) = target  # type: ignore[reportGeneralTypeIssues]

        # Find related decisions in the same project
        cursor = await conn.execute(
            "SELECT id, content, fact_type, created_at, tags "
            "FROM facts "
            "WHERE project = ? AND is_tombstoned = 0 "
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
            "WHERE project = ? AND is_tombstoned = 0 "
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
            n_pred = len(predecessors)  # type: ignore[reportArgumentType]
            lines.append(f"── Preceding Context ({n_pred} entries) ──")
            for p in reversed(predecessors[-10:]):  # type: ignore[reportIndexIssue]
                pid, pcontent, ptype, pcreated, _ptags = p
                lines.append(f"  [{pcreated}] #{pid} ({ptype}): {pcontent[:120]}")
            lines.append("")

        lines.append("  ──── ★ TARGET DECISION ────")
        lines.append(f"  [{tcreated}] #{tid} ({ttype}): {tcontent[:200]}")
        lines.append("")

        if successors:
            n_succ = len(successors)  # type: ignore[reportArgumentType]
            lines.append(f"── Subsequent Impact ({n_succ} entries) ──")
            for s in successors[:5]:  # type: ignore[reportIndexIssue]
                sid, scontent, stype, screated, _stags = s
                lines.append(f"  [{screated}] #{sid} ({stype}): {scontent[:120]}")

        lines.extend(["", "═" * 40])
        return "\n".join(lines)
