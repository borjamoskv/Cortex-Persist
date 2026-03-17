"""Consensus Mixin for AsyncCortexEngine."""

from __future__ import annotations

import logging
import sqlite3
<<<<<<< HEAD
from typing import Any
=======
from typing import Any, Optional
>>>>>>> origin/main

import aiosqlite

from cortex.consensus.vote_ledger import ImmutableVoteLedger
from cortex.engine.mixins.base import EngineMixinBase

logger = logging.getLogger("cortex.engine.consensus")


class ConsensusMixin(EngineMixinBase):
    """Mixin for consensus and voting logic in AsyncCortexEngine."""

<<<<<<< HEAD
    async def _resolve_agent_rep(
        self, conn: aiosqlite.Connection, target_agent_id: str, tenant_id: str = "default"
    ) -> float:
        """Resolve agent reputation, auto-registering if necessary."""
        async with conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ? AND tenant_id = ?",
            (target_agent_id, tenant_id),
=======
    async def _resolve_agent_rep(self, conn: aiosqlite.Connection, target_agent_id: str) -> float:
        """Resolve agent reputation, auto-registering if necessary."""
        async with conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ?", (target_agent_id,)
>>>>>>> origin/main
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]

        # Auto-register any agent that reaches the engine (trusting caller)
        is_human = target_agent_id == "human"
        initial_rep = 1.0 if is_human else 0.5
        await conn.execute(
<<<<<<< HEAD
            "INSERT INTO agents (id, name, agent_type, reputation_score, public_key, tenant_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
=======
            "INSERT INTO agents (id, name, agent_type, reputation_score, public_key) "
            "VALUES (?, ?, ?, ?, '')",
>>>>>>> origin/main
            (
                target_agent_id,
                target_agent_id.capitalize(),
                "human" if is_human else "ai",
                initial_rep,
<<<<<<< HEAD
                "",
                tenant_id,
=======
>>>>>>> origin/main
            ),
        )
        return initial_rep

<<<<<<< HEAD
    async def _update_vote_score(
        self, conn: aiosqlite.Connection, fact_id: int, tenant_id: str = "default"
    ) -> float:
=======
    async def _update_vote_score(self, conn: aiosqlite.Connection, fact_id: int) -> float:
>>>>>>> origin/main
        """Recalculate the consensus score for a given fact."""
        async with conn.execute(
            "SELECT v.vote, v.vote_weight, a.reputation_score "
            "FROM consensus_votes_v2 v "
            "JOIN agents a ON v.agent_id = a.id "
<<<<<<< HEAD
            "WHERE v.fact_id = ? AND v.tenant_id = ? AND a.is_active = 1",
            (fact_id, tenant_id),
=======
            "WHERE v.fact_id = ? AND a.is_active = 1",
            (fact_id,),
>>>>>>> origin/main
        ) as cursor:
            votes = await cursor.fetchall()

        if not votes:
            return 1.0

        weighted_sum = sum(v[0] * max(v[1], v[2]) for v in votes)
        total_weight = sum(max(v[1], v[2]) for v in votes)
        return 1.0 + (weighted_sum / total_weight) if total_weight > 0 else 1.0

    async def vote(
<<<<<<< HEAD
        self, fact_id: int, agent: str, value: int, signature: str | None = None
=======
        self, fact_id: int, agent: str, value: int, signature: Optional[str] = None
>>>>>>> origin/main
    ) -> float:
        """Vote with immutable ledger logging and reputation-weighted consensus."""
        if value not in (-1, 0, 1):
            raise ValueError("Vote must be -1, 0, or 1")

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            from cortex.engine_async import TX_BEGIN_IMMEDIATE

            await conn.execute(TX_BEGIN_IMMEDIATE)
            try:
                # 1. Resolve agent_id and reputation
<<<<<<< HEAD
                async with conn.execute(
                    "SELECT tenant_id FROM facts WHERE id = ?", (fact_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                tenant_id = row[0] if row else "default"

                rep = await self._resolve_agent_rep(conn, agent, tenant_id=tenant_id)

                # 2. Append to Immutable Vote Ledger
                ledger = ImmutableVoteLedger(conn)
                await self._store_consensus_vote(conn, fact_id, agent, value, rep, tenant_id)
=======
                rep = await self._resolve_agent_rep(conn, agent)

                # 2. Append to Immutable Vote Ledger
                ledger = ImmutableVoteLedger(conn)
                await self._store_consensus_vote(conn, fact_id, agent, value, rep)
>>>>>>> origin/main

                # 3. Log transaction
                await self._log_transaction(  # type: ignore[reportAttributeAccessIssue]
                    conn,
                    "consensus",
                    "vote_v2",
<<<<<<< HEAD
                    {"fact_id": fact_id, "agent_id": agent, "vote": value, "tenant_id": tenant_id},
                    tenant_id=tenant_id,
                )

                # 4. Record in permanent immutable ledger
                await ledger.append_vote(
                    fact_id,
                    agent,
                    value,
                    tenant_id=tenant_id,
                    vote_weight=rep,
                    signature=signature,
                )

                # 5. Recalculate score and update fact
                score = await self._update_vote_score(conn, fact_id, tenant_id)
=======
                    {"fact_id": fact_id, "agent_id": agent, "vote": value},
                )

                # 4. Record in permanent immutable ledger
                await ledger.append_vote(fact_id, agent, value, rep, signature)

                # 5. Recalculate score and update fact
                score = await self._update_vote_score(conn, fact_id)
>>>>>>> origin/main
                conf = self._resolve_confidence(score)

                from cortex.engine.mutation_engine import MUTATION_ENGINE

<<<<<<< HEAD
=======
                async with conn.execute(
                    "SELECT tenant_id FROM facts WHERE id = ?", (fact_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                tenant_id = row[0] if row else "default"

>>>>>>> origin/main
                await MUTATION_ENGINE.apply(
                    conn,
                    fact_id=fact_id,
                    tenant_id=tenant_id,
                    event_type="score_update",
                    payload={"consensus_score": score, "confidence": conf},
                    signer="consensus_engine_mixin",
                    commit=False,
                )

                await conn.commit()
                return score
            except (sqlite3.Error, OSError, ValueError) as e:
                await conn.rollback()
                raise e

    async def _store_consensus_vote(
<<<<<<< HEAD
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        agent: str,
        value: int,
        rep: float,
        tenant_id: str = "default",
=======
        self, conn: aiosqlite.Connection, fact_id: int, agent: str, value: int, rep: float
>>>>>>> origin/main
    ) -> None:
        """Helper to store or delete a vote in the consensus table."""
        if value == 0:
            await conn.execute(
<<<<<<< HEAD
                "DELETE FROM consensus_votes_v2 "
                "WHERE fact_id = ? AND agent_id = ? AND tenant_id = ?",
                (fact_id, agent, tenant_id),
=======
                "DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",
                (fact_id, agent),
>>>>>>> origin/main
            )
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO consensus_votes_v2 "
<<<<<<< HEAD
                "(fact_id, agent_id, tenant_id, vote, vote_weight, agent_rep_at_vote) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (fact_id, agent, tenant_id, value, rep, rep),
=======
                "(fact_id, agent_id, vote, vote_weight, agent_rep_at_vote) VALUES (?, ?, ?, ?, ?)",
                (fact_id, agent, value, rep, rep),
>>>>>>> origin/main
            )

    @staticmethod
    def _resolve_confidence(score: float) -> str:
        """Determine confidence label from score."""
        if score >= 1.5:
            return "verified"
        if score <= 0.5:
            return "disputed"
        return "stated"

<<<<<<< HEAD
    async def get_votes(self, fact_id: int, tenant_id: str = "default") -> list[dict[str, Any]]:
=======
    async def get_votes(self, fact_id: int) -> list[dict[str, Any]]:
>>>>>>> origin/main
        """Get all votes for a fact from the canonical v2 table."""
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            conn.row_factory = aiosqlite.Row
            query = """SELECT v.vote, v.agent_id as agent, v.created_at, a.reputation_score
                       FROM consensus_votes_v2 v
                       JOIN agents a ON v.agent_id = a.id
<<<<<<< HEAD
                       WHERE v.fact_id = ? AND v.tenant_id = ?"""
            async with conn.execute(query, (fact_id, tenant_id)) as cursor:
                return [dict(r) for r in await cursor.fetchall()]

    async def verify_vote_ledger(self, tenant_id: str = "default") -> dict[str, Any]:
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            ledger = ImmutableVoteLedger(conn)
            return await ledger.verify_chain_integrity(tenant_id=tenant_id)
=======
                       WHERE v.fact_id = ?"""
            async with conn.execute(query, (fact_id,)) as cursor:
                return [dict(r) for r in await cursor.fetchall()]

    async def verify_vote_ledger(self) -> dict[str, Any]:
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            ledger = ImmutableVoteLedger(conn)
            return await ledger.verify_chain_integrity()
>>>>>>> origin/main
