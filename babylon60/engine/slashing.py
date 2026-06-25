# [C5-REAL] Exergy-Maximized
"""
Sovereign Slashing Primitive (Axiom Ω₃) - CORTEX Persist.
Defines the penalty hooks for reputation destruction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

logger = logging.getLogger("babylon60.engine.slashing")


@dataclass
class SlashingPenalty:
    """Penalty types and their default exergy impacts."""

    MINOR_DEVIATION = 0.05
    MAJOR_DEVIATION = 0.20
    CRYPTOGRAPHIC_TAINT = 0.50
    BYZANTINE_BEHAVIOR = 1.0  # Full annihilation


class SlashingEngine:
    """Executes reputation slashing against the Agent registry."""

    @staticmethod
    async def slash(
        conn: aiosqlite.Connection,
        agent_id: str,
        penalty_type: float,
        reason: str,
        tenant_id: str = "default",
    ) -> float:
        """Slash the reputation of an agent in the DB and return the new score."""
        async with conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ? AND tenant_id = ?",
            (agent_id, tenant_id),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                logger.warning("Attempted to slash non-existent agent: %s", agent_id)
                return 0.0

            old_rep = row[0]
            new_rep = max(0.0, old_rep - penalty_type)

            await conn.execute(
                "UPDATE agents SET "
                "reputation_score = ?, "
                "updated_at = datetime('now') "
                "WHERE id = ? AND tenant_id = ?",
                (new_rep, agent_id, tenant_id),
            )

            logger.info(
                "SLASHED agent %s: %f -> %f (Reason: %s)", agent_id, old_rep, new_rep, reason
            )
            return new_rep
