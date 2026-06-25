# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

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
        """Strict provenance and lineage check. No retrieval inference."""
        if fact_type not in ("decision", "hypothesis"):
            return {"allow_mutation": True, "reason": "ok", "trace_depth": 0}

        # Check if the fact itself has the audited flag
        if meta.get("archaeology_audited") is True:
            return {"allow_mutation": True, "reason": "ok", "trace_depth": 1}

        # Check the trace depth (lineage) by counting previous events
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM entity_events WHERE tenant_id = ?", (tenant_id,)
        )
        row = await cursor.fetchone()
        trace_depth = row[0] if row else 0

        # Look for explicit lineage hooks
        cursor_audit = await conn.execute(
            "SELECT timestamp FROM entity_events WHERE event_type = 'archaeology_merge' AND tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        row_audit = await cursor_audit.fetchone()

        has_audit_trail = "audit_trail" in meta

        if not row_audit and not has_audit_trail:
            return {
                "allow_mutation": False,
                "reason": "missing_lineage",
                "trace_depth": trace_depth,
            }

        return {"allow_mutation": True, "reason": "ok", "trace_depth": trace_depth}
