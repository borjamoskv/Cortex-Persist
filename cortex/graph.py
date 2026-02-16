"""
CORTEX v4.0 — Graph Memory.

Lightweight knowledge graph built from stored facts.
Extracts entities and relationships using heuristic rules (no LLM needed).
Stores everything in SQLite for zero-dependency operation.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("cortex.graph")

__all__ = [
    "Entity",
    "Relationship",
    "extract_entities",
    "detect_relationships",
    "process_fact_graph",
    "get_graph",
    "query_entity",
    "get_entity_types_summary",
]

# ─── Data Models ─────────────────────────────────────────────────────


@dataclass
class Entity:
    """A named entity extracted from facts."""

    id: int = 0
    name: str = ""
    entity_type: str = "unknown"  # person, project, tool, concept, org, file
    project: str = ""
    first_seen: str = ""
    last_seen: str = ""
    mention_count: int = 1
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.entity_type,
            "project": self.project,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "mentions": self.mention_count,
        }


@dataclass
class Relationship:
    """A relationship between two entities."""

    id: int = 0
    source_entity_id: int = 0
    target_entity_id: int = 0
    relation_type: str = "related_to"  # uses, depends_on, created_by, etc.
    weight: float = 1.0
    first_seen: str = ""
    source_fact_id: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source_entity_id,
            "target": self.target_entity_id,
            "type": self.relation_type,
            "weight": self.weight,
        }


# ─── Entity Type Patterns ───────────────────────────────────────────

# Heuristic patterns for entity extraction (no LLM needed)
ENTITY_PATTERNS: list[tuple[str, re.Pattern]] = [
    # File paths
    ("file", re.compile(r"(?:^|[\s`\"\'])([a-zA-Z_][\w]*\.(?:py|js|ts|tsx|jsx|css|html|md|yml|yaml|json|toml|rs|go|sql))\b")),
    # Python/JS modules and classes (PascalCase)
    ("class", re.compile(r"\b([A-Z][a-zA-Z0-9]{2,}(?:[A-Z][a-z]+)+)\b")),
    # Tool/technology names (common ones)
    ("tool", re.compile(
        r"\b(SQLite|FastAPI|Redis|Docker|Kubernetes|PostgreSQL|MySQL|"
        r"React|Vue|Next\.js|Vite|Tailwind|Python|TypeScript|JavaScript|"
        r"GitHub|GitLab|AWS|GCP|Azure|Vercel|Netlify|"
        r"OpenAI|Anthropic|Claude|GPT|LangChain|LlamaIndex|"
        r"Mem0|Zep|Letta|MemGPT|Cognee|"
        r"pytest|uvicorn|pip|npm|node|cargo|"
        r"sqlite-vec|sentence-transformers|ONNX|MCP)\b", re.IGNORECASE)),
    # URLs/domains
    ("url", re.compile(r"(https?://[^\s<>\"']+|[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-z]{2,})")),
    # Project names (lowercase-with-dashes pattern)
    ("project", re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+){1,})\b")),
]

# Relationship signal words
RELATION_SIGNALS: dict[str, list[str]] = {
    "uses": ["uses", "using", "used", "with", "via", "through"],
    "depends_on": ["depends on", "requires", "needs", "dependency"],
    "created_by": ["created by", "built by", "made by", "authored by", "written by"],
    "replaces": ["replaces", "replaced", "instead of", "migrated from"],
    "extends": ["extends", "inherits", "based on", "derived from"],
    "contains": ["contains", "includes", "has", "with"],
    "deployed_to": ["deployed to", "hosted on", "runs on", "deployed on"],
    "integrates": ["integrates with", "connects to", "integrated"],
}


# Common words that match the project pattern but aren't project names
_COMMON_WORDS: frozenset[str] = frozenset({
    "how-to", "set-up", "built-in", "run-time", "self-hosted",
    "up-to", "opt-in", "opt-out", "plug-in", "add-on",
    "on-premise", "on-prem", "re-run", "re-use", "pre-built",
    "well-known", "long-term", "short-term", "real-time",
    "open-source", "third-party", "end-to", "out-of",
    "read-only", "write-only", "read-write",
    "day-to", "step-by", "one-to", "many-to",
    "high-level", "low-level", "top-level",
    # Merged from duplicate definition (was dead code at EOF)
    "the-end", "to-do", "per-day", "per-hour",
    "day-one", "end-of",
    "on-the", "in-the", "at-the", "by-the", "for-the",
    "non-null", "non-empty", "pre-commit", "post-commit",
})


# ─── Extraction ──────────────────────────────────────────────────────


def extract_entities(content: str) -> list[dict]:
    """Extract entities from fact content using heuristic patterns.

    Returns a list of dicts with 'name' and 'entity_type' keys.
    No LLM needed — pure regex + rules.
    """
    if not content or not content.strip():
        return []

    seen: set[str] = set()
    entities: list[dict] = []

    for entity_type, pattern in ENTITY_PATTERNS:
        for match in pattern.finditer(content):
            name = match.group(1).strip()
            # Normalize
            name_lower = name.lower()
            # Skip too short, too long, or already seen
            if len(name) < 2 or len(name) > 100 or name_lower in seen:
                continue
            # Skip common English words for project pattern
            if entity_type == "project" and name_lower in _COMMON_WORDS:
                continue
            seen.add(name_lower)
            entities.append({"name": name, "entity_type": entity_type})

    return entities


def detect_relationships(
    content: str, entities: list[dict]
) -> list[dict]:
    """Detect relationships between entities in the same fact.

    Returns list of dicts with 'source', 'target', 'relation_type'.
    """
    if len(entities) < 2:
        return []

    relationships: list[dict] = []
    content_lower = content.lower()

    # Detect explicit relationship signals
    detected_relation = "related_to"
    for relation_type, signals in RELATION_SIGNALS.items():
        for signal in signals:
            if signal in content_lower:
                detected_relation = relation_type
                break
        if detected_relation != "related_to":
            break

    # Create pairwise relationships for co-occurring entities
    # (entities mentioned in the same fact are related)
    for i, source in enumerate(entities):
        for target in entities[i + 1:]:
            # Don't relate entities of the same name
            if source["name"].lower() == target["name"].lower():
                continue
            relationships.append({
                "source_name": source["name"],
                "target_name": target["name"],
                "relation_type": detected_relation,
            })

    return relationships


# ─── Database Operations ─────────────────────────────────────────────


def upsert_entity(
    conn: sqlite3.Connection,
    name: str,
    entity_type: str,
    project: str,
    timestamp: str,
) -> int:
    """Insert or update an entity. Returns entity ID."""
    # Check if entity already exists for this project
    row = conn.execute(
        "SELECT id, mention_count FROM entities WHERE name = ? AND project = ?",
        (name, project),
    ).fetchone()

    if row:
        entity_id, count = row
        conn.execute(
            "UPDATE entities SET mention_count = ?, last_seen = ? WHERE id = ?",
            (count + 1, timestamp, entity_id),
        )
        return entity_id
    else:
        cursor = conn.execute(
            """INSERT INTO entities (name, entity_type, project, first_seen, last_seen, mention_count)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (name, entity_type, project, timestamp, timestamp),
        )
        return cursor.lastrowid


def upsert_relationship(
    conn: sqlite3.Connection,
    source_id: int,
    target_id: int,
    relation_type: str,
    fact_id: int,
    timestamp: str,
) -> int:
    """Insert or strengthen a relationship. Returns relationship ID."""
    row = conn.execute(
        "SELECT id, weight FROM entity_relations "
        "WHERE source_entity_id = ? AND target_entity_id = ?",
        (source_id, target_id),
    ).fetchone()

    if row:
        rel_id, weight = row
        conn.execute(
            "UPDATE entity_relations SET weight = ?, relation_type = ? WHERE id = ?",
            (weight + 0.5, relation_type, rel_id),
        )
        return rel_id
    else:
        cursor = conn.execute(
            """INSERT INTO entity_relations
               (source_entity_id, target_entity_id, relation_type, weight, first_seen, source_fact_id)
               VALUES (?, ?, ?, 1.0, ?, ?)""",
            (source_id, target_id, relation_type, timestamp, fact_id),
        )
        return cursor.lastrowid


def process_fact_graph(
    conn: sqlite3.Connection,
    fact_id: int,
    content: str,
    project: str,
    timestamp: str,
) -> tuple[int, int]:
    """Extract entities and relationships from a fact and store them.

    Returns (entities_added, relationships_added).
    """
    entities = extract_entities(content)
    if not entities:
        return 0, 0

    relationships = detect_relationships(content, entities)

    # Upsert all entities
    entity_ids: dict[str, int] = {}
    try:
        for ent in entities:
            eid = upsert_entity(conn, ent["name"], ent["entity_type"], project, timestamp)
            entity_ids[ent["name"]] = eid

        # Upsert relationships
        rels_added = 0
        for rel in relationships:
            src_id = entity_ids.get(rel["source_name"])
            tgt_id = entity_ids.get(rel["target_name"])
            if src_id and tgt_id:
                upsert_relationship(conn, src_id, tgt_id, rel["relation_type"], fact_id, timestamp)
                rels_added += 1
    except Exception as e:
        logger.warning("Graph extraction failed for fact #%d: %s", fact_id, e)
        return 0, 0

    return len(entities), rels_added


# ─── Query Operations ────────────────────────────────────────────────


def get_graph(
    conn: sqlite3.Connection,
    project: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """Return the full entity graph for a project.

    Returns dict with 'entities' and 'relationships' arrays,
    plus 'stats' summary.
    """
    # Fetch entities
    if project:
        entity_rows = conn.execute(
            "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
            "FROM entities WHERE project = ? ORDER BY mention_count DESC LIMIT ?",
            (project, limit),
        ).fetchall()
    else:
        entity_rows = conn.execute(
            "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
            "FROM entities ORDER BY mention_count DESC LIMIT ?",
            (limit,),
        ).fetchall()

    entities = []
    entity_ids = set()
    for row in entity_rows:
        entity_ids.add(row[0])
        entities.append({
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "project": row[3],
            "first_seen": row[4],
            "last_seen": row[5],
            "mentions": row[6],
        })

    # Fetch relationships between these entities
    if entity_ids:
        placeholders = ",".join("?" * len(entity_ids))
        id_list = list(entity_ids)
        rel_rows = conn.execute(
            "SELECT id, source_entity_id, target_entity_id, relation_type, weight "
            "FROM entity_relations "
            "WHERE source_entity_id IN (" + placeholders + ") "
            "OR target_entity_id IN (" + placeholders + ")",
            id_list + id_list,
        ).fetchall()
    else:
        rel_rows = []

    relationships = []
    for row in rel_rows:
        relationships.append({
            "id": row[0],
            "source": row[1],
            "target": row[2],
            "type": row[3],
            "weight": row[4],
        })

    # Stats
    total_entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    total_rels = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]

    return {
        "entities": entities,
        "relationships": relationships,
        "stats": {
            "total_entities": total_entities,
            "total_relationships": total_rels,
            "shown_entities": len(entities),
            "shown_relationships": len(relationships),
        },
    }


def query_entity(
    conn: sqlite3.Connection,
    name: str,
    project: Optional[str] = None,
) -> Optional[dict]:
    """Look up a specific entity and its connections."""
    if not name or not name.strip():
        return None
    if project:
        row = conn.execute(
            "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
            "FROM entities WHERE name = ? AND project = ?",
            (name, project),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
            "FROM entities WHERE name = ? ORDER BY mention_count DESC LIMIT 1",
            (name,),
        ).fetchone()

    if not row:
        return None

    entity = {
        "id": row[0], "name": row[1], "type": row[2], "project": row[3],
        "first_seen": row[4], "last_seen": row[5], "mentions": row[6],
    }

    # Get connected entities
    connections = conn.execute(
        """SELECT e.name, e.entity_type, er.relation_type, er.weight
           FROM entity_relations er
           JOIN entities e ON (
               CASE WHEN er.source_entity_id = ? THEN er.target_entity_id
                    ELSE er.source_entity_id END = e.id
           )
           WHERE er.source_entity_id = ? OR er.target_entity_id = ?
           ORDER BY er.weight DESC LIMIT 20""",
        (row[0], row[0], row[0]),
    ).fetchall()

    entity["connections"] = [
        {"name": c[0], "type": c[1], "relation": c[2], "weight": c[3]}
        for c in connections
    ]

    return entity


def get_entity_types_summary(
    conn: sqlite3.Connection,
    project: Optional[str] = None,
) -> list[dict]:
    """Get counts of entities grouped by type."""
    if project:
        rows = conn.execute(
            "SELECT entity_type, COUNT(*) as cnt FROM entities "
            "WHERE project = ? GROUP BY entity_type ORDER BY cnt DESC",
            (project,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT entity_type, COUNT(*) as cnt FROM entities "
            "GROUP BY entity_type ORDER BY cnt DESC",
        ).fetchall()

    return [{"type": r[0], "count": r[1]} for r in rows]

