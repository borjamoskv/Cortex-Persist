# [C5-REAL] Exergy-Maximized

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

__all__ = ["SQLiteStoreMixin"]


class SQLiteStoreMixin:
    """Mixin for graph storage operations."""

    def __init__(self, conn):
        self.conn = conn
        self._is_async = isinstance(conn, aiosqlite.Connection)

    async def upsert_entity(
        self,
        name: str,
        entity_type: str,
        project: str,
        timestamp: str,
        tenant_id: str = "default",
    ) -> int:
        query_select = (
            "SELECT id, mention_count FROM entities WHERE name = ? AND project = ? "
            "AND tenant_id = ?"
        )
        params = (name, project, tenant_id)

        if self._is_async:
            async with self.conn.execute(query_select, params) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(query_select, params).fetchone()

        if row:
            entity_id, count = row
            query_update = "UPDATE entities SET mention_count = ?, last_seen = ? WHERE id = ?"
            if self._is_async:
                await self.conn.execute(query_update, (count + 1, timestamp, entity_id))
            else:
                self.conn.execute(query_update, (count + 1, timestamp, entity_id))
            return entity_id
        query_insert = (
            "INSERT INTO entities (name, entity_type, project, tenant_id, "
            "first_seen, last_seen, mention_count) VALUES (?, ?, ?, ?, ?, ?, 1)"
        )
        params_insert = (name, entity_type, project, tenant_id, timestamp, timestamp)
        if self._is_async:
            async with self.conn.execute(query_insert, params_insert) as cursor:
                return cursor.lastrowid
        else:
            cursor = self.conn.execute(query_insert, params_insert)
            return cursor.lastrowid

    def upsert_entity_sync(
        self,
        name: str,
        entity_type: str,
        project: str,
        timestamp: str,
        tenant_id: str = "default",
    ) -> int:
        cursor = self.conn.execute(
            "SELECT id, mention_count FROM entities WHERE name = ? AND project = ? "
            "AND tenant_id = ?",
            (name, project, tenant_id),
        )
        row = cursor.fetchone()

        if row:
            entity_id, count = row
            self.conn.execute(
                "UPDATE entities SET mention_count = ?, last_seen = ? WHERE id = ?",
                (count + 1, timestamp, entity_id),
            )
            return entity_id
        cursor = self.conn.execute(
            "INSERT INTO entities (name, entity_type, project, tenant_id, first_seen, "
            "last_seen, mention_count) VALUES (?, ?, ?, ?, ?, ?, 1)",
            (name, entity_type, project, tenant_id, timestamp, timestamp),
        )
        return cursor.lastrowid

    async def upsert_relationship(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        fact_id: int,
        timestamp: str,
        tenant_id: str = "default",
    ) -> int:
        query_select = (
            "SELECT id, weight FROM entity_relations WHERE source_entity_id = ? "
            "AND target_entity_id = ? AND tenant_id = ?"
        )
        params = (source_id, target_id, tenant_id)

        if self._is_async:
            async with self.conn.execute(query_select, params) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(query_select, params).fetchone()

        if row:
            rel_id, weight = row
            query_update = "UPDATE entity_relations SET weight = ?, relation_type = ? WHERE id = ?"
            if self._is_async:
                await self.conn.execute(query_update, (weight + 0.5, relation_type, rel_id))
            else:
                self.conn.execute(query_update, (weight + 0.5, relation_type, rel_id))
            return rel_id
        query_insert = (
            "INSERT INTO entity_relations (source_entity_id, target_entity_id, "
            "relation_type, weight, first_seen, source_fact_id, tenant_id) "
            "VALUES (?, ?, ?, 1.0, ?, ?, ?)"
        )
        params_insert = (source_id, target_id, relation_type, timestamp, fact_id, tenant_id)
        if self._is_async:
            async with self.conn.execute(query_insert, params_insert) as cursor:
                return cursor.lastrowid
        else:
            cursor = self.conn.execute(query_insert, params_insert)
            return cursor.lastrowid

    def upsert_relationship_sync(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        fact_id: int,
        timestamp: str,
        tenant_id: str = "default",
    ) -> int:
        cursor = self.conn.execute(
            "SELECT id, weight FROM entity_relations WHERE source_entity_id = ? "
            "AND target_entity_id = ? AND tenant_id = ?",
            (source_id, target_id, tenant_id),
        )
        row = cursor.fetchone()

        if row:
            rel_id, weight = row
            self.conn.execute(
                "UPDATE entity_relations SET weight = ?, relation_type = ? WHERE id = ?",
                (weight + 0.5, relation_type, rel_id),
            )
            return rel_id
        cursor = self.conn.execute(
            "INSERT INTO entity_relations (source_entity_id, target_entity_id, "
            "relation_type, weight, first_seen, source_fact_id, tenant_id) "
            "VALUES (?, ?, ?, 1.0, ?, ?, ?)",
            (source_id, target_id, relation_type, timestamp, fact_id, tenant_id),
        )
        return cursor.lastrowid

    async def upsert_ghost(
        self,
        reference: str,
        context: str,
        project: str,
        timestamp: str,
        tenant_id: str = "default",
    ) -> int:
        q_sel = (
            "SELECT id FROM ghosts WHERE reference = ? AND project = ? AND "
            "tenant_id = ? AND status = 'open'"
        )
        params = (reference, project, tenant_id)
        if self._is_async:
            async with self.conn.execute(q_sel, params) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(q_sel, params).fetchone()
        if row:
            return row[0]
        q_ins = (
            "INSERT INTO ghosts (reference, context, project, tenant_id, detected_at, "
            "status) VALUES (?, ?, ?, ?, ?, 'open')"
        )
        if self._is_async:
            async with self.conn.execute(
                q_ins, (reference, context, project, tenant_id, timestamp)
            ) as cursor:
                return cursor.lastrowid
        else:
            return self.conn.execute(
                q_ins, (reference, context, project, tenant_id, timestamp)
            ).lastrowid

    async def resolve_ghost(
        self,
        ghost_id: int,
        target_id: int,
        confidence: float,
        timestamp: str,
        tenant_id: str = "default",
    ) -> bool:
        q = (
            "UPDATE ghosts SET status = 'resolved', resolved_at = ?, target_id = ?, "
            "confidence = ? WHERE id = ? AND tenant_id = ?"
        )
        if self._is_async:
            async with self.conn.execute(
                q, (timestamp, target_id, confidence, ghost_id, tenant_id)
            ) as cursor:
                return cursor.rowcount > 0
        else:
            return (
                self.conn.execute(
                    q, (timestamp, target_id, confidence, ghost_id, tenant_id)
                ).rowcount
                > 0
            )

    async def delete_fact_elements(self, fact_id: int, tenant_id: str = "default") -> bool:
        q = "DELETE FROM entity_relations WHERE source_fact_id = ? AND tenant_id = ?"
        params = (fact_id, tenant_id)
        if self._is_async:
            async with self.conn.execute(q, params) as cursor:
                return cursor.rowcount > 0
        else:
            return self.conn.execute(q, params).rowcount > 0
