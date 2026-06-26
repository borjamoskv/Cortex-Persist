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

logger = logging.getLogger("cortex.engine.uncategorized.slashing")


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
