"""Consensus Mixin for AsyncCortexEngine."""

from __future__ import annotations

import logging
import sqlite3
from decimal import Decimal
from typing import Any

import aiosqlite

from cortex.consensus.vote_ledger import ImmutableVoteLedger
from cortex.engine.mixins.base import EngineMixinBase

logger = logging.getLogger("cortex.engine.consensus")


class ConsensusMixin(EngineMixinBase):
    """Mixin for consensus and voting logic in AsyncCortexEngine."""

    async def _resolve_agent_rep(self, conn: aiosqlite.Connection, target_agent_id: str) -> Decimal:
        """Resolve agent reputation, auto-registering if necessary."""
        async with conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ?", (target_agent_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Decimal(str(row[0]))

        # Auto-register any agent that reaches the engine (trusting caller)
        is_human = target_agent_id == "human"
        initial_rep = Decimal("1.0") if is_human else Decimal("0.5")
        await conn.execute(
            "INSERT INTO agents (id, name, agent_type, reputation_score, public_key) "
            "VALUES (?, ?, ?, ?, '')",
            (
                target_agent_id,
                target_agent_id.capitalize(),
                "human" if is_human else "ai",
                float(initial_rep),
            ),
        )
        return initial_rep

    async def _update_vote_score(self, conn: aiosqlite.Connection, fact_id: int) -> Decimal:
        """Recalculate the consensus score for a given fact."""
        async with conn.execute(
            "SELECT v.vote, v.vote_weight, a.reputation_score "
            "FROM consensus_votes_v2 v "
            "JOIN agents a ON v.agent_id = a.id "
            "WHERE v.fact_id = ? AND a.is_active = 1",
            (fact_id,),
        ) as cursor:
            votes = await cursor.fetchall()

        if not votes:
            return Decimal("1.0")

        # Convert to Decimal for high-precision sum
        weighted_sum = sum(
            (Decimal(str(v[0])) * max(Decimal(str(v[1])), Decimal(str(v[2]))) for v in votes),
            Decimal("0"),
        )
        total_weight = sum(
            (max(Decimal(str(v[1])), Decimal(str(v[2]))) for v in votes),
            Decimal("0"),
        )

        if total_weight > 0:
            return Decimal("1.0") + (weighted_sum / total_weight)
        return Decimal("1.0")

    async def vote(
        self, fact_id: int, agent: str, value: int, signature: str | None = None
    ) -> Decimal:
        """Vote with immutable ledger logging and reputation-weighted consensus."""
        if value not in (-1, 0, 1):
            raise ValueError("Vote must be -1, 0, or 1")

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            from cortex.engine_async import TX_BEGIN_IMMEDIATE

            await conn.execute(TX_BEGIN_IMMEDIATE)
            try:
                # 1. Resolve agent_id and reputation
                rep = await self._resolve_agent_rep(conn, agent)

                # 2. Append to Immutable Vote Ledger
                ledger = ImmutableVoteLedger(conn)
                await self._store_consensus_vote(conn, fact_id, agent, value, rep)

                # 3. Log transaction
                async with conn.execute(
                    "SELECT tenant_id FROM facts WHERE id = ?", (fact_id,)
                ) as cursor:
                    fact_row = await cursor.fetchone()
                tenant_id = fact_row[0] if fact_row else "default"

                await self._log_transaction(  # type: ignore[reportAttributeAccessIssue]
                    conn,
                    "consensus",
                    "vote_v2",
                    {"fact_id": fact_id, "agent_id": agent, "vote": value},
                    tenant_id=tenant_id,
                )

                # 4. Record in permanent immutable ledger
                await ledger.append_vote(fact_id, agent, value, rep, signature)

                # 5. Recalculate score and update fact
                score = await self._update_vote_score(conn, fact_id)
                conf = self._resolve_confidence(score)

                from cortex.engine.mutation_engine import MUTATION_ENGINE

                await MUTATION_ENGINE.apply(
                    conn,
                    fact_id=fact_id,
                    tenant_id=tenant_id,
                    event_type="score_update",
                    payload={"consensus_score": float(score), "confidence": conf},
                    signer="consensus_engine_mixin",
                    commit=False,
                )

                await conn.commit()
                return score
            except (sqlite3.Error, OSError, ValueError) as e:
                await conn.rollback()
                raise e

    async def _store_consensus_vote(
        self, conn: aiosqlite.Connection, fact_id: int, agent: str, value: int, rep: Decimal
    ) -> None:
        """Helper to store or delete a vote in the consensus table."""
        if value == 0:
            await conn.execute(
                "DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",
                (fact_id, agent),
            )
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO consensus_votes_v2 "
                "(fact_id, agent_id, vote, vote_weight, agent_rep_at_vote) VALUES (?, ?, ?, ?, ?)",
                (fact_id, agent, value, float(rep), float(rep)),
            )

    @staticmethod
    def _resolve_confidence(score: Decimal) -> str:
        """Determine confidence label from score."""
        if score >= Decimal("1.5"):
            return "verified"
        if score <= Decimal("0.5"):
            return "disputed"
        return "stated"

    async def get_votes(self, fact_id: int) -> list[dict[str, Any]]:
        """Get all votes for a fact from the canonical v2 table."""
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            conn.row_factory = aiosqlite.Row
            query = """SELECT v.vote, v.agent_id as agent, v.created_at, a.reputation_score
                       FROM consensus_votes_v2 v
                       JOIN agents a ON v.agent_id = a.id
                       WHERE v.fact_id = ?"""
            async with conn.execute(query, (fact_id,)) as cursor:
                return [dict(r) for r in await cursor.fetchall()]

    async def verify_vote_ledger(self, tenant_id: str = "default") -> dict[str, Any]:
        del tenant_id
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            ledger = ImmutableVoteLedger(conn)
            return await ledger.verify_chain_integrity()

    async def create_vote_checkpoint(self, tenant_id: str = "default") -> str | None:
        del tenant_id
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            ledger = ImmutableVoteLedger(conn)
            return await ledger.create_checkpoint()
