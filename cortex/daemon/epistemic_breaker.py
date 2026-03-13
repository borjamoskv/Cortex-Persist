"""Epistemic Circuit Breaker.

Detiene la ejecución del sistema y dispara `autodidact-omega` si el
ratio de Entropía Cognitiva (ED) excede el umbral de seguridad.
"""

from __future__ import annotations

import logging

import aiosqlite

logger = logging.getLogger("cortex.breaker")


class EpistemicCircuitBreaker:
    """Monitor termodinámico de errores cognitivos. Frena al agente si ED > 50."""

    ED_THRESHOLD = 50.0
    WINDOW_SIZE = 100

    @classmethod
    async def evaluate(cls, conn: aiosqlite.Connection, tenant_id: str, project: str) -> bool:
        """
        Evaluate Entropy Density (ED) in the current context window synchronously.
        If ED > ED_THRESHOLD, triggers a circuit break.
        """
        try:
            # Query the last WINDOW_SIZE facts for this project
            query = """
                SELECT fact_type 
                FROM facts 
                WHERE tenant_id = ? AND project = ?
                ORDER BY id DESC 
                LIMIT ?
            """
            cursor = await conn.execute(query, (tenant_id, project, cls.WINDOW_SIZE))
            rows = await cursor.fetchall()

            if not rows:
                return False

            ghosts = sum(1 for row in rows if row[0] in ("ghost", "error"))
            decisions = sum(1 for row in rows if row[0] in ("decision", "knowledge", "bridge"))

            # Calculate Entropy Density (ED)
            ed = (ghosts / (decisions + 1)) * 100

            logger.debug(
                "[BREAKER] Entropy Density: %.2f%% (Ghosts: %d, Decisions: %d)",
                ed,
                ghosts,
                decisions,
            )

            if ed > cls.ED_THRESHOLD:
                # Trigger circuit break
                await cls._trigger_break(conn, tenant_id, project, ed, ghosts, decisions)
                return True

            return False

        except RuntimeError:
            # We want the circuit breaker halt to bubble up to stop the execution loop.
            raise
        except Exception as e:  # noqa: BLE001
            logger.error("[BREAKER] Error evaluating epistemic circuit: %s", e)
            return False

    @classmethod
    async def _trigger_break(
        cls,
        conn: aiosqlite.Connection,
        tenant_id: str,
        project: str,
        ed: float,
        ghosts: int,
        decisions: int,
    ) -> None:
        """Trigger the break and record the event."""
        logger.critical(
            "🛑 [EPISTEMIC_CIRCUIT_BREAKER] TRIGGERED FOR PROJECT %s. ED: %.2f%%", project, ed
        )
        msg = (
            f"COGNITIVE ENTROPY THRESHOLD EXCEEDED (ED: {ed:.2f}%). "
            "Execution halted. Autodidact-omega required."
        )

        from cortex.engine.fact_store_core import insert_fact_record
        from cortex.memory.temporal import now_iso

        meta = {
            "breaker": "epistemic-circuit-breaker",
            "ed_score": ed,
            "ghosts": ghosts,
            "decisions": decisions,
            "action": "HALTED",
        }

        # Record the breaker event
        await insert_fact_record(
            conn=conn,
            tenant_id=tenant_id,
            project=project,
            content=msg,
            fact_type="error",
            tags=["circuit-break", "system-halt"],
            confidence="C5",
            ts=now_iso(),
            source="daemon:epistemic_breaker",
            meta=meta,
            tx_id=None,
        )
        await conn.commit()

        # Emit a signal via the SignalBus
        try:
            from cortex.signals.bus import AsyncSignalBus

            bus = AsyncSignalBus(conn)
            await bus.emit(
                "EPISTEMIC_BREAK",
                {"project": project, "tenant_id": tenant_id, "ed": ed},
                source="daemon:epistemic_breaker",
            )
        except Exception as e:  # noqa: BLE001
            logger.error("[BREAKER] Failed to emit signal: %s", e)

        raise RuntimeError(msg)
