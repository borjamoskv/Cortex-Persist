# [C5-REAL] Exergy-Maximized
"""Execution Trace Ledger - The Memory Thermodynamics Graph (v19).

Records the flow of energy between hypotheses, tracking cost, lineage,
and outcome without inferring retrieval validity.
"""

from __future__ import annotations

import json
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

logger = logging.getLogger("cortex.ledger.execution_trace")


class ExecutionTraceLedger:
    """Manages the Execution Trace Ledger (Memory Thermodynamics Graph)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._feedback_kernel = None
        self._rollback_engine = None

    def set_feedback_kernel(self, kernel: Any) -> None:
        """Inyecta el kernel de feedback (Ley2Loop)."""
        self._feedback_kernel = kernel

    def set_rollback_engine(self, engine: Any) -> None:
        """Inyecta el motor de rollback causal."""
        self._rollback_engine = engine

    async def record_trace(
        self,
        trace_id: str,
        origin: str,
        cost: float,
        lineage: list[str],
        outcome: str,
        rollback_possible: bool,
        tenant_id: str = "default",
    ) -> None:
        """Records a new execution trace into the ledger.

        Args:
            trace_id: Unique identifier for the mutation event.
            origin: The source or agent that originated the mutation.
            cost: The energetic or computational cost of the mutation.
            lineage: List of parent trace IDs (provenance).
            outcome: Resulting state (e.g., 'falsified', 'crystallized', 'pending').
            rollback_possible: Whether this mutation can be cleanly reverted.
            tenant_id: Multi-tenant boundary.
        """
        query = """
            INSERT INTO execution_trace_ledger
            (id, tenant_id, origin, cost, lineage, outcome, rollback_possible)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        lineage_json = json.dumps(lineage)

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("PRAGMA busy_timeout = 5000;")
                await conn.execute("PRAGMA journal_mode = WAL;")
                await conn.execute(
                    query,
                    (
                        trace_id,
                        tenant_id,
                        origin,
                        cost,
                        lineage_json,
                        outcome,
                        rollback_possible,
                    ),
                )
                await conn.commit()
            logger.debug(
                "Recorded execution trace %s (cost=%.2f, outcome=%s)", trace_id, cost, outcome
            )

            # Cierre termodinámico (Ley 2)
            if self._feedback_kernel:
                import asyncio

                # Trigger thermodynamic feedback loop en background fire-and-forget
                asyncio.create_task(self._feedback_kernel.apply_feedback(tenant_id=tenant_id))

        except Exception as e:
            logger.error("Failed to record execution trace %s: %s", trace_id, e)
            raise

    async def get_trace(self, trace_id: str, tenant_id: str = "default") -> dict[str, Any] | None:
        """Retrieves a trace from the ledger."""
        query = "SELECT * FROM execution_trace_ledger WHERE id = ? AND tenant_id = ?"
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA busy_timeout = 5000;")
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, (trace_id, tenant_id))
            row = await cursor.fetchone()
            if not row:
                return None

            return {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "origin": row["origin"],
                "cost": row["cost"],
                "lineage": json.loads(row["lineage"]),
                "outcome": row["outcome"],
                "rollback_possible": bool(row["rollback_possible"]),
                "created_at": row["created_at"],
            }

    async def get_recent(
        self, limit: int = 500, tenant_id: str = "default"
    ) -> list[dict[str, Any]]:
        """Retrieves recent execution traces for feedback mapping."""
        query = "SELECT * FROM execution_trace_ledger WHERE tenant_id = ? ORDER BY id DESC LIMIT ?"
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA busy_timeout = 5000;")
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, (tenant_id, limit))
            rows = await cursor.fetchall()

            return [
                {
                    "id": r["id"],
                    "tenant_id": r["tenant_id"],
                    "origin": r["origin"],
                    "cost": r["cost"],
                    "lineage": json.loads(r["lineage"]),
                    "outcome": r["outcome"],
                    "rollback_possible": bool(r["rollback_possible"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    async def query_by_lineage(
        self, lineage_hash: str, tenant_id: str = "default"
    ) -> list[dict[str, Any]]:
        """Busca todas las trazas que compartan un hash de linaje."""
        # Se busca el lineage_hash dentro del array JSON
        query = "SELECT * FROM execution_trace_ledger WHERE tenant_id = ? AND lineage LIKE ?"
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA busy_timeout = 5000;")
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, (tenant_id, f"%{lineage_hash}%"))
            rows = await cursor.fetchall()

            return [
                {
                    "id": r["id"],
                    "tenant_id": r["tenant_id"],
                    "origin": r["origin"],
                    "cost": r["cost"],
                    "lineage": json.loads(r["lineage"]),
                    "outcome": r["outcome"],
                    "rollback_possible": bool(r["rollback_possible"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
