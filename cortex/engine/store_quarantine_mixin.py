"""store_quarantine_mixin — Quarantine / Unquarantine lifecycle for the Store Layer.

Extracted from StoreMixin to satisfy the Landauer LOC barrier (≤500).
Handles the forensic isolation protocol: facts remain in DB for audit,
excluded from recall, search, and dedup.
"""

from __future__ import annotations

import logging

import aiosqlite

from cortex.memory.temporal import now_iso

__all__ = ["QuarantineMixin"]

logger = logging.getLogger("cortex")


class QuarantineMixin:
    """Forensic isolation layer. Quarantined facts are excluded from
    recall, search, and dedup but remain in DB for immutable audit."""

    async def quarantine(
        self,
        fact_id: int,
        reason: str,
        conn: aiosqlite.Connection | None = None,
    ) -> bool:
        """Quarantine a fact: isolate without deleting.

        Quarantined facts are excluded from recall, search, and dedup.
        They remain in the DB for forensic analysis.
        """
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")
        if not reason or not reason.strip():
            raise ValueError("Quarantine reason is required")

        from cortex.engine.mutation_engine import MUTATION_ENGINE

        async def _impl(c: aiosqlite.Connection) -> bool:
            ts = now_iso()
            cursor = await c.execute(
                "SELECT tenant_id FROM facts "
                "WHERE id = ? AND valid_until IS NULL "
                "AND is_quarantined = 0",
                (fact_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return False

            await MUTATION_ENGINE.apply(
                c,
                fact_id=fact_id,
                tenant_id=row[0],
                event_type="quarantine",
                payload={"reason": reason.strip(), "timestamp": ts},
                signer="store_mixin:quarantine",
                commit=False,
            )
            await self._log_transaction(  # type: ignore[reportAttributeAccessIssue]
                c,
                "system",
                "quarantine",
                {"fact_id": fact_id, "reason": reason},
            )
            await c.commit()
            return True

        if conn:
            return await _impl(conn)
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            return await _impl(conn)  # type: ignore[reportArgumentType]

    async def unquarantine(
        self,
        fact_id: int,
        conn: aiosqlite.Connection | None = None,
    ) -> bool:
        """Lift quarantine from a fact."""
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")

        from cortex.engine.mutation_engine import MUTATION_ENGINE

        async def _impl(c: aiosqlite.Connection) -> bool:
            ts = now_iso()
            cursor = await c.execute(
                "SELECT tenant_id FROM facts WHERE id = ? AND is_quarantined = 1",
                (fact_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return False

            await MUTATION_ENGINE.apply(
                c,
                fact_id=fact_id,
                tenant_id=row[0],
                event_type="unquarantine",
                payload={"timestamp": ts},
                signer="store_mixin:unquarantine",
                commit=False,
            )
            await self._log_transaction(  # type: ignore[reportAttributeAccessIssue]
                c,
                "system",
                "unquarantine",
                {"fact_id": fact_id},
            )
            await c.commit()
            return True

        if conn:
            return await _impl(conn)
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            return await _impl(conn)  # type: ignore[reportArgumentType]
