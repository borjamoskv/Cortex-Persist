"""Graph Processing Engine.

Extraction, relationship detection, and backend orchestration.
"""

from __future__ import annotations

import logging
import sqlite3

from cortex.graph.backends import GraphBackend, SQLiteBackend
from cortex.graph.patterns import COMMON_WORDS, ENTITY_PATTERNS, RELATION_SIGNALS

__all__ = [
    "detect_relationships",
    "extract_entities",
    "find_path",
    "get_backend",
    "get_context_subgraph",
    "get_graph",
    "get_graph_sync",
    "process_fact_graph",
    "process_fact_graph_sync",
    "query_entity",
    "query_entity_sync",
]

logger = logging.getLogger("cortex.graph")


def get_backend(conn=None) -> GraphBackend:
    """Get the appropriate graph backend."""
    return SQLiteBackend(conn)  # type: ignore[arg-type]


def extract_entities(content: str) -> list[dict]:
    """Extract entities from text content using regex patterns."""
    if not content or not content.strip():
        return []
    seen: set[str] = set()
    entities: list[dict] = []
    for entity_type, pattern in ENTITY_PATTERNS:
        for match in pattern.finditer(content):
            name = match.group(1).strip()
            name_lower = name.lower()
            if len(name) < 2 or len(name) > 100 or name_lower in seen:
                continue
            if entity_type == "project" and name_lower in COMMON_WORDS:
                continue
            seen.add(name_lower)
            entities.append({"name": name, "entity_type": entity_type})
    return entities


def detect_relationships(content: str, entities: list[dict]) -> list[dict]:
    """Detect relationships between extracted entities via signal matching."""
    if len(entities) < 2:
        return []
    relationships: list[dict] = []
    content_lower = content.lower()
    detected_relation = "related_to"
    for relation_type, signals in RELATION_SIGNALS.items():
        for signal in signals:
            if signal in content_lower:
                detected_relation = relation_type
                break
        if detected_relation != "related_to":
            break
    for i, source in enumerate(entities):
        for target in entities[i + 1 :]:
            if source["name"].lower() == target["name"].lower():
                continue
            relationships.append(
                {
                    "source_name": source["name"],
                    "target_name": target["name"],
                    "relation_type": detected_relation,
                }
            )
    return relationships


async def _upsert_entity(
    conn, ent: dict, project: str, timestamp: str, tenant_id: str = "default"
) -> int:
    """Upsert a single entity, returning its ID."""
    cursor = await conn.execute(
        "SELECT id, mention_count FROM entities WHERE name = ? AND project = ? AND tenant_id = ?",
        (ent["name"], project, tenant_id),
    )
    row = await cursor.fetchone()
    if row:
        entity_id, count = row
        await conn.execute(
            "UPDATE entities SET mention_count = ?, last_seen = ? WHERE id = ?",
            (count + 1, timestamp, entity_id),
        )
        return entity_id
    cursor = await conn.execute(
        "INSERT INTO entities "
        "(name, entity_type, project, tenant_id, first_seen, last_seen, mention_count) "
        "VALUES (?, ?, ?, ?, ?, ?, 1)",
        (ent["name"], ent["entity_type"], project, tenant_id, timestamp, timestamp),
    )
    return cursor.lastrowid  # type: ignore[return-value]


async def _upsert_relation(
    conn,
    sid: int,
    tid: int,
    relation_type: str,
    timestamp: str,
    fact_id: int,
    tenant_id: str = "default",
) -> None:
    """Upsert a single relation between two entities."""
    cursor = await conn.execute(
        "SELECT id, weight FROM entity_relations "
        "WHERE source_entity_id = ? AND target_entity_id = ? AND tenant_id = ?",
        (sid, tid, tenant_id),
    )
    row = await cursor.fetchone()
    if row:
        rel_id, weight = row
        await conn.execute(
            "UPDATE entity_relations SET weight = ?, relation_type = ? WHERE id = ?",
            (weight + 0.5, relation_type, rel_id),
        )
    else:
        await conn.execute(
            "INSERT INTO entity_relations "
            "(source_entity_id, target_entity_id, relation_type, "
            "weight, first_seen, source_fact_id, tenant_id) "
            "VALUES (?, ?, ?, 1.0, ?, ?, ?)",
            (sid, tid, relation_type, timestamp, fact_id, tenant_id),
        )


async def process_fact_graph(
    conn, fact_id: int, content: str, project: str, timestamp: str, tenant_id: str = "default"
) -> tuple[int, int]:
    """Process a fact for graph extraction (async)."""
    entities = extract_entities(content)
    if not entities:
        return 0, 0
    relationships = detect_relationships(content, entities)

    try:
        entity_ids: dict[str, int] = {}
        for ent in entities:
            entity_ids[ent["name"]] = await _upsert_entity(conn, ent, project, timestamp, tenant_id)

        for rel in relationships:
            sid = entity_ids.get(rel["source_name"])
            tid = entity_ids.get(rel["target_name"])
            if sid and tid:
                await _upsert_relation(
                    conn, sid, tid, rel["relation_type"], timestamp, fact_id, tenant_id
                )

        return len(entities), len(relationships)
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.warning("Graph processing failed for fact %d (tenant=%s): %s", fact_id, tenant_id, e)
        return 0, 0


def process_fact_graph_sync(
    conn, fact_id: int, content: str, project: str, timestamp: str, tenant_id: str = "default"
) -> tuple[int, int]:
    """Process a fact for graph extraction (sync)."""
    entities = extract_entities(content)
    if not entities:
        return 0, 0
    relationships = detect_relationships(content, entities)

    try:
        backend = get_backend(conn)
        entity_ids: dict[str, int] = {}
        for ent in entities:
            eid = backend.upsert_entity_sync(  # type: ignore[reportAttributeAccessIssue]
                ent["name"], ent["entity_type"], project, timestamp, tenant_id
            )
            entity_ids[ent["name"]] = eid

        for rel in relationships:
            source_id = entity_ids.get(rel["source_name"])
            target_id = entity_ids.get(rel["target_name"])
            if source_id and target_id:
                backend.upsert_relationship_sync(  # type: ignore[reportAttributeAccessIssue]
                    source_id, target_id, rel["relation_type"], fact_id, timestamp, tenant_id
                )
        return len(entities), len(relationships)
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.warning(
            "Graph processing sync failed for fact %d (tenant=%s): %s", fact_id, tenant_id, e
        )
        return 0, 0


async def get_graph(
    conn, project: str | None = None, limit: int = 50, tenant_id: str = "default"
) -> dict:
    """Get graph data for a project or all projects.

    Args:
        conn: Active database connection.
        project: Optional project filter.
        limit: Maximum entities to return.
        tenant_id: Multi-tenant isolation ID.
    """
    backend = get_backend(conn)
    return await backend.get_graph(project, limit, tenant_id)  # type: ignore[reportCallIssue]


def get_graph_sync(
    conn, project: str | None = None, limit: int = 50, tenant_id: str = "default"
) -> dict:
    """Get graph data synchronously."""
    backend = get_backend(conn)
    return backend.get_graph_sync(project, limit, tenant_id)  # type: ignore[reportAttributeAccessIssue]


async def query_entity(
    conn, name: str, project: str | None = None, tenant_id: str = "default"
) -> dict | None:
    """Query a specific entity by name.

    Args:
        conn: Active database connection.
        name: Entity name to search for.
        project: Optional project filter.
        tenant_id: Multi-tenant isolation ID.
    """
    backend = get_backend(conn)
    return await backend.query_entity(name, project, tenant_id)  # type: ignore[reportCallIssue]


def query_entity_sync(
    conn, name: str, project: str | None = None, tenant_id: str = "default"
) -> dict | None:
    """Query entity synchronously."""
    backend = get_backend(conn)
    return backend.query_entity_sync(name, project, tenant_id)  # type: ignore[reportAttributeAccessIssue]


async def find_path(
    conn, source: str, target: str, max_depth: int = 3, tenant_id: str = "default"
) -> list[dict]:
    """Find meaningful paths between two entities.

    Useful for explaining connections (e.g., "How is Project A related to Library B?").
    """
    backend = get_backend(conn)
    return await backend.find_path(source, target, max_depth, tenant_id)  # type: ignore[reportCallIssue]


async def get_context_subgraph(
    conn, seeds: list[str], depth: int = 2, max_nodes: int = 50, tenant_id: str = "default"
) -> dict:
    """Retrieve a subgraph context for RAG.

    Given a list of seed entities (e.g. from a user query), expand the graph
    to find relevant context.
    """
    backend = get_backend(conn)
    return await backend.find_context_subgraph(seeds, depth, max_nodes, tenant_id)  # type: ignore[reportCallIssue]
