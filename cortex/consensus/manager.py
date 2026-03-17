"""Consensus Sovereign Layer — ConsensusManager for CORTEX."""

from __future__ import annotations

import logging
import math
import uuid

from cortex.telemetry.metrics import metrics
from cortex.telemetry.pulse import PULSE

__all__ = ["ConsensusManager"]

logger = logging.getLogger("cortex.consensus")


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1.0 - 1e-6)
    return math.log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    if x > 500:
        return 1.0
    if x < -500:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


class ConsensusManager:
    """Manages agent registration and weighted consensus voting."""

    def __init__(self, engine, signal_bus=None):
        self.engine = engine
        self._signal_bus = signal_bus or getattr(engine, "_signal_bus", None)

    async def vote(
        self,
        fact_id: int,
        agent: str,
        value: int,
        agent_id: str | None = None,
    ) -> float:
        """Legacy v1 vote path. DEPRECATED. Use vote_v2 instead."""
        import warnings

        warnings.warn(
            "ConsensusManager.vote() is deprecated and will be removed. Use vote_v2().",
            DeprecationWarning,
            stacklevel=2,
        )

        if agent_id:
            return await self.vote_v2(fact_id, agent_id, value)

        if value not in (-1, 0, 1):
            raise ValueError(f"vote value must be -1, 0, or 1, got {value}")

        conn = await self.engine.get_conn()

        if value == 0:
            await conn.execute(
                "DELETE FROM consensus_votes WHERE fact_id = ? AND agent = ?",
                (fact_id, agent),
            )
            action = "unvote"
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO consensus_votes (fact_id, agent, vote) VALUES (?, ?, ?)",
                (fact_id, agent, value),
            )
            action = "vote"

        await self.engine._log_transaction(
            conn,
            "consensus",
            action,
            {"fact_id": fact_id, "agent": agent, "vote": value},
        )
        # 💓 Pulse Signal (Reality Observer)
        if self._signal_bus:
            self._signal_bus.emit(
                f"consensus:{action}",
                payload={"fact_id": fact_id, "agent": agent, "vote": value},
                source="consensus_manager",
            )

        score = await self._recalculate_consensus(fact_id, conn)
        await conn.commit()
        return score

    async def register_agent(
        self,
        name: str,
        agent_type: str = "ai",
        public_key: str = "",
        tenant_id: str = "default",
    ) -> str:
        agent_id = str(uuid.uuid4())
        conn = await self.engine.get_conn()
        await conn.execute(
            "INSERT INTO agents "
            "(id, name, agent_type, public_key, tenant_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (agent_id, name, agent_type, public_key, tenant_id),
        )
        await conn.commit()
        return agent_id

    async def vote_v2(
        self,
        fact_id: int,
        agent_id: str,
        value: int,
        reason: str | None = None,
    ) -> float:
        if value not in (-1, 0, 1):
            raise ValueError(f"vote value must be -1, 0, or 1, got {value}")

        conn = await self.engine.get_conn()
        cursor = await conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ? AND is_active = 1",
            (agent_id,),
        )
        agent = await cursor.fetchone()
        if not agent:
            # 💓 Pulse Reality Check: agent missing
            if self._signal_bus:
                self._signal_bus.emit(
                    "error:consensus:agent_not_found",
                    payload={"agent_id": agent_id, "fact_id": fact_id},
                    source="consensus_manager",
                )

            # Legacy Shadow (Analyzing a corpse)
            metrics.inc(
                "cortex_consensus_failures_total",
                labels={"reason": "agent_not_found"},
                meta={"agent_id": agent_id, "fact_id": fact_id},
            )
            # Notify Pulse Registry of the shadow detection
            PULSE.inc(
                "cortex_consensus_failures_shadow_total", labels={"reason": "agent_not_found"}
            )

            raise ValueError(f"Agent {agent_id} not found")

        rep = agent[0]

        if value == 0:
            await conn.execute(
                "DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",
                (fact_id, agent_id),
            )
            action = "unvote_v2"
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO consensus_votes_v2 "
                "(fact_id, agent_id, vote, vote_weight, agent_rep_at_vote, vote_reason) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (fact_id, agent_id, value, rep, rep, reason),
            )
            action = "vote_v2"

        await self.engine._log_transaction(
            conn,
            "consensus",
            action,
            {
                "fact_id": fact_id,
                "agent_id": agent_id,
                "vote": value,
                "rep": rep,
                "reason": reason,
            },
        )
        score = await self._recalculate_consensus_v2(fact_id, conn)
        await conn.commit()
        return score

    async def _recalculate_consensus_v2(self, fact_id: int, conn) -> float:
        cursor = await conn.execute(
            "SELECT v.vote, v.vote_weight, a.reputation_score "
            "FROM consensus_votes_v2 v "
            "JOIN agents a ON v.agent_id = a.id "
            "WHERE v.fact_id = ? AND a.is_active = 1",
            (fact_id,),
        )
        votes = await cursor.fetchall()
        if not votes:
            return await self._recalculate_consensus(fact_id, conn)

        # Logarithmic Opinion Pool (LogOP) consensus calculation
        score_sum = 0.0
        for v in votes:
            vote_val = v[0]
            if vote_val == 0:
                continue

            p = 0.99 if vote_val > 0 else 0.01
            # Quadratic weight aggressively suppresses unreliable nodes
            rel = max(v[1], v[2])
            w = rel**2

            score_sum += w * _logit(p)

        prob_true = _sigmoid(score_sum)
        # Scale back to [0.0, 2.0] so >=1.5 is verified
        score = prob_true * 2.0

        await self._update_fact_score(fact_id, score, conn)

        # 🛡️ Aplicar Penalización de Entropía (Alignment Drift)
        await self._update_agent_entropy(fact_id, score, conn)

        return score

    async def _recalculate_consensus(self, fact_id: int, conn) -> float:
        cursor = await conn.execute(
            "SELECT vote FROM consensus_votes WHERE fact_id = ?",
            (fact_id,),
        )
        votes = await cursor.fetchall()
        if not votes:
            score = 1.0
            await self._update_fact_score(fact_id, score, conn)
            return score

        score_sum = 0.0
        for (vote_val,) in votes:
            if vote_val == 0:
                continue
            p = 0.99 if vote_val > 0 else 0.01
            w = 1.0  # Legacy votes have equal weight
            score_sum += w * _logit(p)

        prob_true = _sigmoid(score_sum)
        score = prob_true * 2.0

        await self._update_fact_score(fact_id, score, conn)
        return score

    async def _update_fact_score(self, fact_id: int, score: float, conn) -> None:
        from cortex.engine.mutation_engine import MUTATION_ENGINE

        if score >= 1.5:
            conf = "verified"
        elif score <= 0.5:
            conf = "disputed"
        else:
            conf = None

        cursor = await conn.execute(
            "SELECT tenant_id FROM facts WHERE id = ?",
            (fact_id,),
        )
        row = await cursor.fetchone()
        tenant_id = row[0] if row else "default"

        payload: dict = {"consensus_score": score}
        if conf:
            payload["confidence"] = conf

        await MUTATION_ENGINE.apply(
            conn,
            fact_id=fact_id,
            tenant_id=tenant_id,
            event_type="score_update",
            payload=payload,
            signer="consensus_manager",
            commit=False,
        )

    async def _update_agent_entropy(self, fact_id: int, final_consensus: float, conn) -> None:
        """
        Ratifica el consenso final y castiga/premia la entropía de los votantes.
        Implementa el decaimiento de reputación por Deriva de Alineación (Ω2 + Ω5).
        """
        # Convertimos score continuo de [0.5, 1.5] a valor discreto
        if final_consensus >= 1.5:
            c_val = 1
        elif final_consensus <= 0.5:
            c_val = -1
        else:
            return  # No hay consenso claro aún (Disputed), no hay castigo posible.

        # 1. Recuperar los votos para este Fact
        cursor = await conn.execute(
            "SELECT agent_id, vote FROM consensus_votes_v2 WHERE fact_id = ?", (fact_id,)
        )
        voters = await cursor.fetchall()

        for agent_id, a_vote in voters:
            # Calcular Alineación (1 = Acierto, -1 = Divergencia, 0 = Abstención)
            alignment_score = a_vote * c_val

            # 2. Actualizar el ring_buffer de los últimos N votos (hits vs misses)
            await conn.execute(
                """
                UPDATE agents 
                SET 
                    alignment_hits = alignment_hits + (CASE WHEN ? > 0 THEN 1 ELSE 0 END),
                    alignment_misses = alignment_misses + (CASE WHEN ? < 0 THEN 1 ELSE 0 END),
                    reputation_score = CASE 
                        WHEN (alignment_hits - alignment_misses) < 0 THEN base_reputation * 0.5
                        ELSE base_reputation 
                    END
                WHERE id = ? AND is_active = 1
            """,
                (alignment_score, alignment_score, agent_id),
            )

            # Pulse the reality degradation check
            if alignment_score < 0:
                logger.warning(
                    "Entropic drift detected in agent %s (Vote rejected by WBFT Consensus).",
                    agent_id,
                )
                if self._signal_bus:
                    self._signal_bus.emit(
                        "agent:alignment:drift",
                        payload={"agent_id": agent_id, "fact_id": fact_id},
                        source="consensus_manager",
                    )
