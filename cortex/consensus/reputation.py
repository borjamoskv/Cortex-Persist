"""Reputation Manager — Sovereign persistence for agent trust (Ω₃).

Manages the lifecycle of agent reputation in the CORTEX Ledger.
Bridges the gap between synchronous consensus logic and asynchronous DB persistence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger("cortex.consensus.reputation")


@dataclass(frozen=True)
class ReputationState:
    """Snapshot of an agent's reputation state."""

    agent_id: str
    score: float
    stake: float
    total_votes: int
    successful_votes: int
    disputed_votes: int
    is_active: bool


class ReputationManager:
    """Handles persistent reputation updates and lookups in the 'agents' table."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get_reputation(self, agent_id: str) -> ReputationState:
        """Fetch current reputation state for an agent."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, reputation_score, reputation_stake, total_votes, "
                "successful_votes, disputed_votes, is_active "
                "FROM agents WHERE id = ?",
                (agent_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    # Auto-register with default score
                    await self._register_agent(db, agent_id)
                    return ReputationState(
                        agent_id=agent_id,
                        score=0.5,
                        stake=0.0,
                        total_votes=0,
                        successful_votes=0,
                        disputed_votes=0,
                        is_active=True,
                    )
                return ReputationState(
                    agent_id=row["id"],
                    score=row["reputation_score"],
                    stake=row["reputation_stake"],
                    total_votes=row["total_votes"],
                    successful_votes=row["successful_votes"],
                    disputed_votes=row["disputed_votes"],
                    is_active=bool(row["is_active"]),
                )

    async def update_score(
        self,
        agent_id: str,
        delta: float,
        reason: str | None = None,
        is_success: bool | None = None,
    ) -> float:
        """Update an agent's reputation score with asymmetric penalty (taint)."""
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Fetch current
            state = await self.get_reputation(agent_id)
            new_score = max(0.0, min(1.0, state.score + delta))

            # 2. Update counters
            success_inc = 1 if is_success is True else 0
            dispute_inc = 1 if is_success is False else 0
            total_inc = 1 if is_success is not None else 0

            await db.execute(
                """
                UPDATE agents 
                SET reputation_score = ?, 
                    total_votes = total_votes + ?,
                    successful_votes = successful_votes + ?,
                    disputed_votes = disputed_votes + ?,
                    last_active_at = ?,
                    meta = json_set(COALESCE(meta, '{}'), '$.last_update_reason', ?)
                WHERE id = ?
                """,
                (
                    new_score,
                    total_inc,
                    success_inc,
                    dispute_inc,
                    datetime.now(timezone.utc).isoformat(),
                    reason or "manual_update",
                    agent_id,
                ),
            )
            await db.commit()
            logger.info(
                "Reputation update for %s: %.3f -> %.3f (%s)",
                agent_id,
                state.score,
                new_score,
                reason,
            )
            return new_score

    async def slash(
        self, agent_id: str, penalty: float = 0.1, reason: str = "byzantine_behavior"
    ) -> float:
        """Heavily penalize an agent for malicious or faulty behavior."""
        # Asymmetric penalty: failures count more (default 0.1 is 10% of total range)
        return await self.update_score(agent_id, -penalty, reason=reason, is_success=False)

    async def reward(
        self, agent_id: str, bonus: float = 0.01, reason: str = "consensus_contribution"
    ) -> float:
        """Small reward for contributing to valid consensus."""
        return await self.update_score(agent_id, bonus, reason=reason, is_success=True)

    async def _register_agent(self, db: aiosqlite.Connection, agent_id: str) -> None:
        """Internal helper to bootstrap a new agent entry."""
        await db.execute(
            "INSERT OR IGNORE INTO agents (id, name, public_key) VALUES (?, ?, '')",
            (agent_id, agent_id.capitalize()),
        )
        await db.commit()
