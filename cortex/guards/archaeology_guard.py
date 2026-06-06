"""Archaeology Guard (Ley 1) - Pre-commit hook to audit history."""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

logger = logging.getLogger("cortex.guards.archaeology")


class ArchaeologyGuard:
    """Enforces Ley 1: Archaeology First.
    
    Blocks new decisions or hypotheses if the historical context (bridges or anamnesis)
    has not been audited.
    """

    async def check_history_audited(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Strict provenance and lineage check. No epistemic inference."""
        if fact_type not in ("decision", "hypothesis"):
            return {"allow_mutation": True, "reason": "ok", "trace_depth": 0}

        # Check if the fact itself has the audited flag
        if meta.get("archaeology_audited") is True:
            return {"allow_mutation": True, "reason": "ok", "trace_depth": 1}

        # Check the trace depth (lineage) by counting previous events
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM entity_events WHERE tenant_id = ?",
            (tenant_id,)
        )
        row = await cursor.fetchone()
        trace_depth = row[0] if row else 0

        # Look for explicit lineage hooks
        cursor_audit = await conn.execute(
            "SELECT timestamp FROM entity_events WHERE event_type = 'archaeology_merge' AND tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,)
        )
        row_audit = await cursor_audit.fetchone()
        
        has_audit_trail = "audit_trail" in meta

        if not row_audit and not has_audit_trail:
            return {
                "allow_mutation": False,
                "reason": "missing_lineage",
                "trace_depth": trace_depth
            }
            
        return {"allow_mutation": True, "reason": "ok", "trace_depth": trace_depth}
