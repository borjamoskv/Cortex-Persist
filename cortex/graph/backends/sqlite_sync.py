# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""SQLite Graph Backend — Synchronous Operations Mixin.

Extracted from sqlite.py to keep file size under 400 LOC.
Contains all *_sync methods that operate on plain sqlite3 connections.
"""

from __future__ import annotations

import logging

__all__ = ["SyncGraphMixin"]

logger = logging.getLogger("cortex.graph.backends")


class SyncGraphMixin:
    """Mixin providing synchronous graph operations for SQLiteBackend.

    Requires the host class to have:
        - self.conn: a sqlite3.Connection
    """

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
