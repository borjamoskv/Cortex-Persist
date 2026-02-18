"""SQLite Graph Store Mixin."""
import aiosqlite

class SQLiteStoreMixin:
    """Mixin for graph storage operations."""

    def __init__(self, conn):
        self.conn = conn
        self._is_async = isinstance(conn, aiosqlite.Connection)

    async def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> int:
        query_select = "SELECT id, mention_count FROM entities WHERE name = ? AND project = ?"
        params = (name, project)

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
        else:
            query_insert = """INSERT INTO entities (name, entity_type, project, first_seen, last_seen, mention_count)
                              VALUES (?, ?, ?, ?, ?, 1)"""
            params_insert = (name, entity_type, project, timestamp, timestamp)
            if self._is_async:
                async with self.conn.execute(query_insert, params_insert) as cursor:
                    return cursor.lastrowid
            else:
                cursor = self.conn.execute(query_insert, params_insert)
                return cursor.lastrowid

    def upsert_entity_sync(self, name: str, entity_type: str, project: str, timestamp: str) -> int:
        cursor = self.conn.execute(
            "SELECT id, mention_count FROM entities WHERE name = ? AND project = ?",
            (name, project),
        )
        row = cursor.fetchone()

        if row:
            entity_id, count = row
            self.conn.execute(
                "UPDATE entities SET mention_count = ?, last_seen = ? WHERE id = ?",
                (count + 1, timestamp, entity_id),
            )
            return entity_id
        else:
            cursor = self.conn.execute(
                """INSERT INTO entities (name, entity_type, project, first_seen, last_seen, mention_count)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (name, entity_type, project, timestamp, timestamp),
            )
            return cursor.lastrowid

    async def upsert_relationship(
        self, source_id: int, target_id: int, relation_type: str, fact_id: int, timestamp: str
    ) -> int:
        query_select = "SELECT id, weight FROM entity_relations WHERE source_entity_id = ? AND target_entity_id = ?"
        params = (source_id, target_id)

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
        else:
            query_insert = """INSERT INTO entity_relations
                               (source_entity_id, target_entity_id, relation_type, weight, first_seen, source_fact_id)
                               VALUES (?, ?, ?, 1.0, ?, ?)"""
            params_insert = (source_id, target_id, relation_type, timestamp, fact_id)
            if self._is_async:
                async with self.conn.execute(query_insert, params_insert) as cursor:
                    return cursor.lastrowid
            else:
                cursor = self.conn.execute(query_insert, params_insert)
                return cursor.lastrowid

    def upsert_relationship_sync(
        self, source_id: int, target_id: int, relation_type: str, fact_id: int, timestamp: str
    ) -> int:
        cursor = self.conn.execute(
            "SELECT id, weight FROM entity_relations WHERE source_entity_id = ? AND target_entity_id = ?",
            (source_id, target_id),
        )
        row = cursor.fetchone()

        if row:
            rel_id, weight = row
            self.conn.execute(
                "UPDATE entity_relations SET weight = ?, relation_type = ? WHERE id = ?",
                (weight + 0.5, relation_type, rel_id),
            )
            return rel_id
        else:
            cursor = self.conn.execute(
                """INSERT INTO entity_relations
                   (source_entity_id, target_entity_id, relation_type, weight, first_seen, source_fact_id)
                   VALUES (?, ?, ?, 1.0, ?, ?)""",
                (source_id, target_id, relation_type, timestamp, fact_id),
            )
            return cursor.lastrowid

    async def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> int:
        q_sel = "SELECT id FROM ghosts WHERE reference = ? AND project = ? AND status = 'open'"
        if self._is_async:
            async with self.conn.execute(q_sel, (reference, project)) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(q_sel, (reference, project)).fetchone()
        if row:
            return row[0]
        q_ins = "INSERT INTO ghosts (reference, context, project, detected_at, status) VALUES (?, ?, ?, ?, 'open')"
        if self._is_async:
            async with self.conn.execute(q_ins, (reference, context, project, timestamp)) as cursor:
                return cursor.lastrowid
        else:
            return self.conn.execute(q_ins, (reference, context, project, timestamp)).lastrowid

    async def resolve_ghost(
        self, ghost_id: int, target_id: int, confidence: float, timestamp: str
    ) -> bool:
        q = "UPDATE ghosts SET status = 'resolved', resolved_at = ?, target_id = ?, confidence = ? WHERE id = ?"
        if self._is_async:
            async with self.conn.execute(q, (timestamp, target_id, confidence, ghost_id)) as cursor:
                return cursor.rowcount > 0
        else:
            return self.conn.execute(q, (timestamp, target_id, confidence, ghost_id)).rowcount > 0

    async def delete_fact_elements(self, fact_id: int) -> bool:
        q = "DELETE FROM entity_relations WHERE source_fact_id = ?"
        if self._is_async:
            async with self.conn.execute(q, (fact_id,)) as cursor:
                return cursor.rowcount > 0
        else:
            return self.conn.execute(q, (fact_id,)).rowcount > 0
