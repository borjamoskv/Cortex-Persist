"""SQLite Graph Query Mixin."""
from typing import Optional

class SQLiteQueryMixin:
    """Mixin for graph query operations."""

    async def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        query_entities = "SELECT id, name, entity_type, project, mention_count FROM entities"
        params_entities = []
        if project:
            query_entities += " WHERE project = ?"
            params_entities.append(project)
        query_entities += " ORDER BY mention_count DESC LIMIT ?"
        params_entities.append(limit)

        if self._is_async:
            async with self.conn.execute(query_entities, params_entities) as cursor:
                entity_rows = await cursor.fetchall()
        else:
            entity_rows = self.conn.execute(query_entities, params_entities).fetchall()

        entities = []
        entity_ids = []
        for row in entity_rows:
            entities.append(
                {"id": row[0], "name": row[1], "type": row[2], "project": row[3], "weight": row[4]}
            )
            entity_ids.append(row[0])

        if not entity_ids:
            return {
                "entities": [],
                "relationships": [],
                "stats": {"total_entities": 0, "total_relationships": 0},
            }

        placeholders = ",".join(["?"] * len(entity_ids))
        query_rels = f"""
            SELECT id, source_entity_id, target_entity_id, relation_type, weight
            FROM entity_relations
            WHERE source_entity_id IN ({placeholders}) OR target_entity_id IN ({placeholders})
        """
        params_rels = entity_ids + entity_ids

        if self._is_async:
            async with self.conn.execute(query_rels, params_rels) as cursor:
                rel_rows = await cursor.fetchall()
        else:
            rel_rows = self.conn.execute(query_rels, params_rels).fetchall()

        relationships = []
        for row in rel_rows:
            relationships.append(
                {"id": row[0], "source": row[1], "target": row[2], "type": row[3], "weight": row[4]}
            )

        # Calculate stats
        total_entities = 0
        total_rels = 0
        if project:
            q_ent_count = "SELECT COUNT(*) FROM entities WHERE project = ?"
            q_rel_count = """SELECT COUNT(*) FROM entity_relations er 
                             JOIN entities e ON er.source_entity_id = e.id 
                             WHERE e.project = ?"""
            if self._is_async:
                async with self.conn.execute(q_ent_count, (project,)) as cursor:
                    total_entities = (await cursor.fetchone())[0]
                async with self.conn.execute(q_rel_count, (project,)) as cursor:
                    total_rels = (await cursor.fetchone())[0]
            else:
                total_entities = self.conn.execute(q_ent_count, (project,)).fetchone()[0]
                total_rels = self.conn.execute(q_rel_count, (project,)).fetchone()[0]
        else:
            q_ent_count = "SELECT COUNT(*) FROM entities"
            q_rel_count = "SELECT COUNT(*) FROM entity_relations"
            if self._is_async:
                async with self.conn.execute(q_ent_count) as cursor:
                    total_entities = (await cursor.fetchone())[0]
                async with self.conn.execute(q_rel_count) as cursor:
                    total_rels = (await cursor.fetchone())[0]
            else:
                total_entities = self.conn.execute(q_ent_count).fetchone()[0]
                total_rels = self.conn.execute(q_rel_count).fetchone()[0]

        return {
            "entities": entities,
            "relationships": relationships,
            "stats": {"total_entities": total_entities, "total_relationships": total_rels},
        }

    def get_graph_sync(self, project: Optional[str] = None, limit: int = 50) -> dict:
        if project:
            entity_rows = self.conn.execute(
                "SELECT id, name, entity_type, project, mention_count "
                "FROM entities WHERE project = ? ORDER BY mention_count DESC LIMIT ?",
                (project, limit),
            ).fetchall()
        else:
            entity_rows = self.conn.execute(
                "SELECT id, name, entity_type, project, mention_count "
                "FROM entities ORDER BY mention_count DESC LIMIT ?",
                (limit,),
            ).fetchall()

        entities = []
        entity_ids = []
        for row in entity_rows:
            entities.append(
                {"id": row[0], "name": row[1], "type": row[2], "project": row[3], "weight": row[4]}
            )
            entity_ids.append(row[0])

        if not entity_ids:
            return {
                "entities": [],
                "relationships": [],
                "stats": {"total_entities": 0, "total_relationships": 0},
            }

        placeholders = ",".join(["?"] * len(entity_ids))
        rel_rows = self.conn.execute(
            f"SELECT id, source_entity_id, target_entity_id, relation_type, weight "
            f"FROM entity_relations WHERE source_entity_id IN ({placeholders}) OR target_entity_id IN ({placeholders})",
            entity_ids + entity_ids,
        ).fetchall()

        relationships = []
        for row in rel_rows:
            relationships.append(
                {"id": row[0], "source": row[1], "target": row[2], "type": row[3], "weight": row[4]}
            )

        if project:
            total_entities = self.conn.execute(
                "SELECT COUNT(*) FROM entities WHERE project = ?", (project,)
            ).fetchone()[0]
            total_rels = self.conn.execute(
                "SELECT COUNT(*) FROM entity_relations er JOIN entities e ON er.source_entity_id = e.id WHERE e.project = ?",
                (project,),
            ).fetchone()[0]
        else:
            total_entities = self.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            total_rels = self.conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]

        return {
            "entities": entities,
            "relationships": relationships,
            "stats": {"total_entities": total_entities, "total_relationships": total_rels},
        }

    async def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        if not name or not name.strip():
            return None

        q_ent = "SELECT id, name, entity_type, project, mention_count FROM entities WHERE name = ?"
        params_ent = [name]
        if project:
            q_ent += " AND project = ?"
            params_ent.append(project)
        else:
            q_ent += " ORDER BY mention_count DESC LIMIT 1"

        if self._is_async:
            async with self.conn.execute(q_ent, params_ent) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(q_ent, params_ent).fetchone()

        if not row:
            return None

        entity = {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "project": row[3],
            "mentions": row[4],
        }

        q_conn = """SELECT e.name, e.entity_type, er.relation_type, er.weight 
                   FROM entity_relations er 
                   JOIN entities e ON (CASE WHEN er.source_entity_id = ? THEN er.target_entity_id ELSE er.source_entity_id END = e.id)
                   WHERE er.source_entity_id = ? OR er.target_entity_id = ?
                   ORDER BY er.weight DESC LIMIT 20"""

        if self._is_async:
            async with self.conn.execute(q_conn, (row[0], row[0], row[0])) as cursor:
                connections = await cursor.fetchall()
        else:
            connections = self.conn.execute(q_conn, (row[0], row[0], row[0])).fetchall()

        entity["connections"] = [
            {"name": c[0], "type": c[1], "relation": c[2], "weight": c[3]} for c in connections
        ]
        return entity

    def query_entity_sync(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        if not name or not name.strip():
            return None
        q = "SELECT id, name, entity_type, project, mention_count FROM entities WHERE name = ?"
        if project:
            row = self.conn.execute(q + " AND project = ?", (name, project)).fetchone()
        else:
            row = self.conn.execute(q + " ORDER BY mention_count DESC LIMIT 1", (name,)).fetchone()

        if not row:
            return None
        entity = {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "project": row[3],
            "mentions": row[4],
        }
        connections = self.conn.execute(
            """SELECT e.name, e.entity_type, er.relation_type, er.weight FROM entity_relations er 
               JOIN entities e ON (CASE WHEN er.source_entity_id = ? THEN er.target_entity_id ELSE er.source_entity_id END = e.id)
               WHERE er.source_entity_id = ? OR er.target_entity_id = ? ORDER BY er.weight DESC LIMIT 20""",
            (row[0], row[0], row[0]),
        ).fetchall()
        entity["connections"] = [
            {"name": c[0], "type": c[1], "relation": c[2], "weight": c[3]} for c in connections
        ]
        return entity
