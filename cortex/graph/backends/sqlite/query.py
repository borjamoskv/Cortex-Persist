"""SQLite Graph Query Mixin."""

__all__ = ["SQLiteQueryMixin"]


class SQLiteQueryMixin:
    """Mixin for graph query operations."""

    async def get_graph(self, project: str | None = None, limit: int = 50) -> dict:
        entities, entity_ids = await self._get_graph_entities(project, limit)

        if not entity_ids:
            return {
                "entities": [],
                "relationships": [],
                "stats": {"total_entities": 0, "total_relationships": 0},
            }

        relationships = await self._get_graph_relationships(entity_ids)
        stats = await self._get_graph_stats(project)

        return {
            "entities": entities,
            "relationships": relationships,
            "stats": stats,
        }

    async def _get_graph_entities(
        self, project: str | None, limit: int
    ) -> tuple[list[dict], list[int]]:
        query_entities = "SELECT id, name, entity_type, project, mention_count FROM entities"
        params_entities = []
        if project:
            query_entities += " WHERE project = ?"
            params_entities.append(project)
        query_entities += " ORDER BY mention_count DESC LIMIT ?"
        params_entities.append(limit)

        entity_rows = await self._fetch_rows(query_entities, params_entities)

        entities = []
        entity_ids = []
        for row in entity_rows:
            entities.append(
                {"id": row[0], "name": row[1], "type": row[2], "project": row[3], "weight": row[4]}
            )
            entity_ids.append(row[0])
        return entities, entity_ids

    async def _get_graph_relationships(self, entity_ids: list[int]) -> list[dict]:
        placeholders = ",".join(["?"] * len(entity_ids))
        query_rels = f"""
            SELECT id, source_entity_id, target_entity_id, relation_type, weight
            FROM entity_relations
            WHERE source_entity_id IN ({placeholders}) OR target_entity_id IN ({placeholders})
        """
        params_rels = entity_ids + entity_ids

        rel_rows = await self._fetch_rows(query_rels, params_rels)

        relationships = []
        for row in rel_rows:
            relationships.append(
                {"id": row[0], "source": row[1], "target": row[2], "type": row[3], "weight": row[4]}
            )
        return relationships

    async def _get_graph_stats(self, project: str | None) -> dict[str, int]:
        total_entities = 0
        total_rels = 0
        if project:
            q_ent_count = "SELECT COUNT(*) FROM entities WHERE project = ?"
            q_rel_count = """SELECT COUNT(*) FROM entity_relations er
                             JOIN entities e ON er.source_entity_id = e.id
                             WHERE e.project = ?"""
            total_entities = (await self._fetch_row(q_ent_count, [project]))[0]
            total_rels = (await self._fetch_row(q_rel_count, [project]))[0]
        else:
            q_ent_count = "SELECT COUNT(*) FROM entities"
            q_rel_count = "SELECT COUNT(*) FROM entity_relations"
            total_entities = (await self._fetch_row(q_ent_count, []))[0]
            total_rels = (await self._fetch_row(q_rel_count, []))[0]

        return {"total_entities": total_entities, "total_relationships": total_rels}

    def get_graph_sync(self, project: str | None = None, limit: int = 50) -> dict:
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

    async def query_entity(self, name: str, project: str | None = None) -> dict | None:
        if not name or not name.strip():
            return None

        q_ent = "SELECT id, name, entity_type, project, mention_count FROM entities WHERE name = ?"
        params_ent = [name]
        if project:
            q_ent += " AND project = ?"
            params_ent.append(project)
        else:
            q_ent += " ORDER BY mention_count DESC LIMIT 1"

        row = await self._fetch_row(q_ent, params_ent)

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

        connections = await self._fetch_rows(q_conn, [row[0], row[0], row[0]])

        entity["connections"] = [
            {"name": c[0], "type": c[1], "relation": c[2], "weight": c[3]} for c in connections
        ]
        return entity

    def query_entity_sync(self, name: str, project: str | None = None) -> dict | None:
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
