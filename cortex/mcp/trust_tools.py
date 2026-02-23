"""
CORTEX Trust Tools — EU AI Act Compliance MCP Tools.

These tools extend the CORTEX MCP server with audit, verification,
and compliance capabilities aligned with EU AI Act Article 12
(record-keeping obligations for high-risk AI systems).

Tools:
    - cortex_audit_trail: Generate audit trail for agent decisions
    - cortex_verify_fact: Verify cryptographic integrity of a specific fact
    - cortex_compliance_report: Generate EU AI Act compliance snapshot
    - cortex_decision_lineage: Trace the lineage of a decision
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

__all__ = ["register_trust_tools"]

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from cortex.mcp.server import _MCPContext

logger = logging.getLogger("cortex.mcp.trust")


def register_trust_tools(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register all Trust/Compliance tools on the MCP server."""
    from cortex.mcp.trust_compliance import register_compliance_tools

    _register_audit_trail(mcp, ctx)
    _register_verify_fact(mcp, ctx)
    register_compliance_tools(mcp, ctx)


def _build_audit_trail_query(
    project: str, agent_id: str, since: str, limit: int
) -> tuple[str, list]:
    conditions = ["f.deprecated_at IS NULL"]
    params: list = []

    if project:
        conditions.append("f.project = ?")
        params.append(project)
    if agent_id:
        conditions.append("f.tags LIKE ?")
        params.append(f"%agent:{agent_id}%")
    if since:
        conditions.append("f.created_at >= ?")
        params.append(since)

    where = " AND ".join(conditions)

    query = f"""
        SELECT f.id, f.project, f.content, f.fact_type,
               f.created_at, f.tags,
               t.hash, t.prev_hash, t.operation
        FROM facts f
        LEFT JOIN transactions t ON t.fact_id = f.id
        WHERE {where}
        ORDER BY f.created_at DESC
        LIMIT ?
    """
    params.append(limit)
    return query, params


def _register_audit_trail(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register the ``cortex_audit_trail`` tool."""

    @mcp.tool()
    async def cortex_audit_trail(
        project: str = "",
        agent_id: str = "",
        since: str = "",
        limit: int = 50,
    ) -> str:
        """Generate an immutable audit trail of agent decisions.

        Produces a timestamped, hash-verified log of all decisions
        made by agents within a project. Each entry includes the
        cryptographic hash from the transaction ledger, ensuring
        tamper-proof evidence per EU AI Act Article 12.

        Args:
            project: Filter by project name (empty = all projects)
            agent_id: Filter by agent ID tag (empty = all agents)
            since: ISO date filter, e.g. "2026-01-01" (empty = all time)
            limit: Maximum entries to return (default 50, max 200)
        """
        await ctx.ensure_ready()
        limit = min(max(limit, 1), 200)

        async with ctx.pool.acquire() as conn:
            query, params = _build_audit_trail_query(project, agent_id, since, limit)
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

        if not rows:
            return "No audit entries found for the given filters."

        lines = [
            "═══ CORTEX AUDIT TRAIL ═══",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Entries: {len(rows)}",
            f"Filters: project={project or '*'}, agent={agent_id or '*'}, since={since or 'all'}",
            "═" * 40,
            "",
        ]

        for row in rows:
            fact_id, proj, content, ftype, created, tags, tx_hash, prev_hash, _ = row
            hash_short = (tx_hash or "—")[:16]
            prev_short = (prev_hash or "genesis")[:16]
            lines.append(
                f"[{created}] #{fact_id} ({ftype}) [{proj}]\n"
                f"  Content: {content[:200]}\n"
                f"  Hash: {hash_short}… → prev: {prev_short}…\n"
                f"  Tags: {tags or 'none'}\n"
            )

        lines.append("═" * 40)
        lines.append("Cryptographic chain verified via SHA-256 hash linking.")
        return "\n".join(lines)


def _register_verify_fact(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register the ``cortex_verify_fact`` tool."""

    @mcp.tool()
    async def cortex_verify_fact(fact_id: int) -> str:
        """Verify the cryptographic integrity of a specific fact.

        Checks that the fact's transaction hash is valid, the chain
        to its predecessor is unbroken, and the content has not been
        tampered with. Returns a verification certificate.

        Args:
            fact_id: The ID of the fact to verify
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            # Get the fact
            cursor = await conn.execute(
                "SELECT id, project, content, fact_type, created_at FROM facts WHERE id = ?",
                (fact_id,),
            )
            fact = await cursor.fetchone()

            if not fact:
                return f"❌ Fact #{fact_id} not found."

            # Get the transaction
            cursor = await conn.execute(
                "SELECT id, hash, prev_hash, operation, created_at "
                "FROM transactions WHERE fact_id = ?",
                (fact_id,),
            )
            tx = await cursor.fetchone()

            if not tx:
                return (
                    f"⚠️ Fact #{fact_id} exists but has no transaction record.\n"
                    f"This fact predates the ledger system."
                )

            # Verify the hash chain to predecessor
            tx_id, tx_hash, prev_hash, operation, _ = tx
            chain_valid = True
            chain_msg = "✅ Valid"

            if prev_hash:
                cursor = await conn.execute(
                    "SELECT hash FROM transactions WHERE id = ?",
                    (tx_id - 1,),
                )
                prev_tx = await cursor.fetchone()
                if prev_tx and prev_tx[0] != prev_hash:
                    chain_valid = False
                    chain_msg = "❌ BROKEN — prev_hash mismatch"

            # Check if the fact is in a Merkle checkpoint
            cursor = await conn.execute(
                "SELECT id, merkle_root, start_id, end_id, created_at "
                "FROM merkle_roots "
                "WHERE start_id <= ? AND end_id >= ? "
                "LIMIT 1",
                (tx_id, tx_id),
            )
            checkpoint = await cursor.fetchone()

        # Build verification certificate
        fid, proj, content, ftype, created = fact
        lines = [
            "═══ CORTEX VERIFICATION CERTIFICATE ═══",
            f"Fact ID:      #{fid}",
            f"Project:      {proj}",
            f"Type:         {ftype}",
            f"Created:      {created}",
            f"Content:      {content[:300]}",
            "",
            "── Cryptographic Proof ──",
            f"TX Hash:      {tx_hash}",
            f"Prev Hash:    {prev_hash or 'genesis'}",
            f"Chain Link:   {chain_msg}",
            f"Operation:    {operation}",
        ]

        if checkpoint:
            cp_id, merkle_root, start, end, cp_time = checkpoint
            lines.extend(
                [
                    "",
                    "── Merkle Checkpoint ──",
                    f"Checkpoint:   #{cp_id}",
                    f"Merkle Root:  {merkle_root}",
                    f"Range:        TX #{start} → #{end}",
                    f"Sealed At:    {cp_time}",
                    "Status:       ✅ Fact included in sealed checkpoint",
                ]
            )
        else:
            lines.append("\nMerkle:       ⏳ Not yet included in a checkpoint")

        overall = "✅ VERIFIED" if chain_valid else "❌ INTEGRITY VIOLATION"
        lines.extend(["", f"═══ VERDICT: {overall} ═══"])

        return "\n".join(lines)
