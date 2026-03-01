"""Quarantine mixin — isolate and release facts for forensic analysis."""

from __future__ import annotations

import logging

import aiosqlite

from cortex.memory.temporal import now_iso

__all__ = ["QuarantineMixin"]

logger = logging.getLogger("cortex")


class QuarantineMixin:
    """Sovereign Quarantine. Isolate suspicious facts without deleting them."""

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

        async def _impl(c: aiosqlite.Connection) -> bool:
            ts = now_iso()
            cursor = await c.execute(
                "UPDATE facts SET is_quarantined = 1, quarantined_at = ?, "
                "quarantine_reason = ?, updated_at = ? "
                "WHERE id = ? AND valid_until IS NULL AND is_quarantined = 0",
                (ts, reason.strip(), ts, fact_id),
            )
            if cursor.rowcount > 0:
                await self._log_transaction(
                    c, "system", "quarantine",
                    {"fact_id": fact_id, "reason": reason},
                )
                await c.commit()
                return True
            return False

        if conn:
            return await _impl(conn)
        async with self.session() as conn:
            return await _impl(conn)

    async def unquarantine(
        self,
        fact_id: int,
        conn: aiosqlite.Connection | None = None,
    ) -> bool:
        """Lift quarantine from a fact."""
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")

        async def _impl(c: aiosqlite.Connection) -> bool:
            ts = now_iso()
            cursor = await c.execute(
                "UPDATE facts SET is_quarantined = 0, quarantined_at = NULL, "
                "quarantine_reason = NULL, updated_at = ? "
                "WHERE id = ? AND is_quarantined = 1",
                (ts, fact_id),
            )
            if cursor.rowcount > 0:
                await self._log_transaction(
                    c, "system", "unquarantine", {"fact_id": fact_id},
                )
                await c.commit()
                return True
            return False

        if conn:
            return await _impl(conn)
        async with self.session() as conn:
            return await _impl(conn)
