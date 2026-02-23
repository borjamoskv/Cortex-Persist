"""Ghost management mixin — register and resolve ghosts."""

from __future__ import annotations

import logging

import aiosqlite

from cortex.temporal import now_iso

logger = logging.getLogger("cortex.ghosts")


class GhostMixin:
    """Logic for managing ghost facts (mentions of entities not yet stored)."""

    async def register_ghost(
        self,
        reference: str,
        context: str,
        project: str,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        if conn:
            return await self._register_ghost_impl(conn, reference, context, project)

        async with self.session() as conn:
            res = await self._register_ghost_impl(conn, reference, context, project)
            await conn.commit()
            return res

    async def _register_ghost_impl(
        self, conn: aiosqlite.Connection, reference: str, context: str, project: str
    ) -> int:
        # Check if exists (idempotency)
        cursor = await conn.execute(
            "SELECT id FROM ghosts WHERE reference = ? AND project = ?",
            (reference, project),
        )
        row = await cursor.fetchone()
        if row:
            return row[0]

        ts = now_iso()
        cursor = await conn.execute(
            "INSERT INTO ghosts "
            "(reference, context, project, status, created_at) "
            "VALUES (?, ?, ?, 'open', ?)",
            (reference, context, project, ts),
        )
        return cursor.lastrowid

    async def resolve_ghost(
        self,
        ghost_id: int,
        target_entity_id: int,
        confidence: float = 1.0,
        conn: aiosqlite.Connection | None = None,
    ) -> bool:
        if conn:
            return await self._resolve_ghost_impl(conn, ghost_id, target_entity_id, confidence)

        async with self.session() as conn:
            res = await self._resolve_ghost_impl(conn, ghost_id, target_entity_id, confidence)
            await conn.commit()
            return res

    async def _resolve_ghost_impl(
        self, conn: aiosqlite.Connection, ghost_id: int, target_entity_id: int, confidence: float
    ) -> bool:
        ts = now_iso()
        cursor = await conn.execute(
            "UPDATE ghosts SET status = 'resolved', target_id = ?, "
            "confidence = ?, resolved_at = ? WHERE id = ?",
            (target_entity_id, confidence, ts, ghost_id),
        )
        return cursor.rowcount > 0
