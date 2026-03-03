"""Open CORTEX — SQLite/Postgres dual persistence layer.

Implements the memories, memory_edges, and memory_audit_log tables
from the Open CORTEX Standard v0.1 specification.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from open_cortex.models import (
    AuditEntry,
    Belief,
    EdgeType,
    Memory,
    Namespace,
    Provenance,
    Relation,
    SourceType,
)

logger = logging.getLogger("open_cortex.persistence")

# ─── Schema DDL ──────────────────────────────────────────────────────

SCHEMA_MEMORIES = """
CREATE TABLE IF NOT EXISTS memories (
    id              TEXT PRIMARY KEY,
    namespace       TEXT NOT NULL DEFAULT 'global'
                    CHECK(namespace IN ('user','team','global')),
    content         TEXT NOT NULL,
    tags            TEXT NOT NULL DEFAULT '[]',
    source          TEXT NOT NULL DEFAULT 'system'
                    CHECK(source IN ('user','agent','document','system','abstraction')),
    method          TEXT NOT NULL DEFAULT 'user_input',
    author          TEXT NOT NULL DEFAULT '',
    document_ref    TEXT DEFAULT '',
    confidence      REAL NOT NULL DEFAULT 0.5
                    CHECK(confidence >= 0.0 AND confidence <= 1.0),
    last_verified   TEXT NOT NULL DEFAULT (datetime('now')),
    calibration_src TEXT DEFAULT '',
    valid_from      TEXT NOT NULL DEFAULT (datetime('now')),
    valid_until     TEXT,
    is_canonical    INTEGER NOT NULL DEFAULT 1,
    version         INTEGER NOT NULL DEFAULT 1,
    parent_id       TEXT REFERENCES memories(id),
    pii             INTEGER NOT NULL DEFAULT 0,
    meta            TEXT DEFAULT '{}',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_mem_namespace   ON memories(namespace);
CREATE INDEX IF NOT EXISTS idx_mem_canonical   ON memories(is_canonical);
CREATE INDEX IF NOT EXISTS idx_mem_confidence  ON memories(confidence);
CREATE INDEX IF NOT EXISTS idx_mem_valid       ON memories(valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_mem_parent      ON memories(parent_id);
CREATE INDEX IF NOT EXISTS idx_mem_source      ON memories(source);
"""

SCHEMA_EDGES = """
CREATE TABLE IF NOT EXISTS memory_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       TEXT NOT NULL REFERENCES memories(id),
    target_id       TEXT NOT NULL REFERENCES memories(id),
    edge_type       TEXT NOT NULL
                    CHECK(edge_type IN ('supports','contradicts','supersedes')),
    reason          TEXT DEFAULT '',
    confidence      REAL DEFAULT 1.0
                    CHECK(confidence >= 0.0 AND confidence <= 1.0),
    created_by      TEXT NOT NULL DEFAULT 'system',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_id, target_id, edge_type)
);
"""

SCHEMA_EDGE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_edge_source ON memory_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edge_target ON memory_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edge_type   ON memory_edges(edge_type);
"""

SCHEMA_AUDIT = """
CREATE TABLE IF NOT EXISTS memory_audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id       TEXT NOT NULL REFERENCES memories(id),
    action          TEXT NOT NULL,
    actor           TEXT NOT NULL,
    prev_state      TEXT,
    new_state       TEXT,
    reason          TEXT DEFAULT '',
    timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_AUDIT_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_audit_mem ON memory_audit_log(memory_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts  ON memory_audit_log(timestamp);
"""

ALL_SCHEMA = [
    SCHEMA_MEMORIES,
    SCHEMA_INDEXES,
    SCHEMA_EDGES,
    SCHEMA_EDGE_INDEXES,
    SCHEMA_AUDIT,
    SCHEMA_AUDIT_INDEXES,
]


# ─── Database Manager ────────────────────────────────────────────────


class MemoryStore:
    """SQLite-backed persistence for the Open CORTEX standard.

    Thread-safe via per-call connections. Designed for easy swap
    to asyncpg/Postgres in production.
    """

    __slots__ = ("_db_path",)

    def __init__(self, db_path: str = "open_cortex.db") -> None:
        self._db_path = db_path
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            for stmt in ALL_SCHEMA:
                conn.executescript(stmt)
            conn.commit()
        logger.info("Schema initialized at %s", self._db_path)

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    # ─── WRITE ────────────────────────────────────────────────────

    def write_memory(self, mem: Memory) -> str:
        """Insert a memory. Returns the memory ID."""
        now = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO memories (
                    id, namespace, content, tags, source, method, author,
                    document_ref, confidence, last_verified, valid_from,
                    valid_until, is_canonical, version, parent_id, pii,
                    meta, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mem.id,
                    mem.namespace.value,
                    mem.content,
                    json.dumps(mem.tags),
                    mem.provenance.source.value,
                    mem.provenance.method.value,
                    mem.provenance.author,
                    mem.provenance.document_ref,
                    mem.belief.confidence,
                    mem.belief.last_verified.isoformat(),
                    mem.freshness.valid_from.isoformat(),
                    mem.freshness.valid_until.isoformat() if mem.freshness.valid_until else None,
                    1 if mem.freshness.is_canonical else 0,
                    mem.version.v,
                    mem.version.parent_id,
                    1 if mem.pii else 0,
                    json.dumps(mem.meta),
                    now,
                    now,
                ),
            )

            # Write edges
            edges_created = 0
            for rel in mem.relations:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO memory_edges
                        (source_id, target_id, edge_type, reason, confidence, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mem.id,
                        rel.target_id,
                        rel.type.value,
                        rel.reason,
                        rel.confidence,
                        mem.provenance.author or "system",
                    ),
                )
                edges_created += 1

                # If supersedes, decanonize the target
                if rel.type == EdgeType.SUPERSEDES:
                    conn.execute(
                        "UPDATE memories SET is_canonical = 0, valid_until = ?, updated_at = ? WHERE id = ?",
                        (now, now, rel.target_id),
                    )

            # Audit log
            conn.execute(
                """
                INSERT INTO memory_audit_log (memory_id, action, actor, new_state, reason)
                VALUES (?, 'create', ?, ?, 'Initial write')
                """,
                (
                    mem.id,
                    mem.provenance.author or "system",
                    json.dumps(mem.model_dump(), default=str),
                ),
            )

            conn.commit()
            logger.info("Wrote memory %s (%d edges)", mem.id, edges_created)
            return mem.id

    # ─── READ ─────────────────────────────────────────────────────

    def get_memory(self, memory_id: str) -> Memory | None:
        """Retrieve a single memory by ID."""
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if not row:
                return None
            return self._row_to_memory(row)

    def search_canonical(
        self,
        *,
        namespace: str | None = None,
        tags: list[str] | None = None,
        min_confidence: float = 0.0,
        k: int = 10,
        text_query: str | None = None,
    ) -> list[Memory]:
        """Search canonical memories with filters. BM25-like text match via LIKE."""
        clauses: list[str] = ["is_canonical = 1"]
        params: list[Any] = []

        if namespace:
            clauses.append("namespace = ?")
            params.append(namespace)
        if min_confidence > 0:
            clauses.append("confidence >= ?")
            params.append(min_confidence)
        if text_query:
            clauses.append("content LIKE ?")
            params.append(f"%{text_query}%")

        where = " AND ".join(clauses)
        sql = f"SELECT * FROM memories WHERE {where} ORDER BY confidence DESC LIMIT ?"
        params.append(k)

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            results = [self._row_to_memory(r) for r in rows]

        # Post-filter by tags if needed
        if tags:
            tag_set = set(tags)
            results = [m for m in results if tag_set & set(m.tags)]

        return results[:k]

    # ─── RECONSOLIDATE ────────────────────────────────────────────

    def reconsolidate(
        self,
        target_id: str,
        new_content: str,
        confidence: float,
        reason: str,
        author: str = "system",
        tags: list[str] | None = None,
    ) -> tuple[str, int]:
        """Create a new canonical memory that supersedes the target.

        Returns (new_memory_id, audit_entry_id).
        """
        old = self.get_memory(target_id)
        if old is None:
            msg = f"Target memory {target_id} not found"
            raise ValueError(msg)

        new_mem = Memory(
            content=new_content,
            tags=tags or old.tags,
            namespace=old.namespace,
            provenance=Provenance(
                source=old.provenance.source,
                method="reconsolidation",
                author=author,
            ),
            belief=Belief(confidence=confidence),
            freshness=old.freshness.model_copy(update={"is_canonical": True}),
            version=old.version.model_copy(
                update={
                    "v": old.version.v + 1,
                    "parent_id": old.id,
                    "lineage": [*old.version.lineage, old.id],
                }
            ),
            relations=[
                Relation(
                    type=EdgeType.SUPERSEDES,
                    target_id=target_id,
                    reason=reason,
                )
            ],
        )

        self.write_memory(new_mem)

        # Get audit entry ID
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM memory_audit_log WHERE memory_id = ? ORDER BY id DESC LIMIT 1",
                (new_mem.id,),
            ).fetchone()
            audit_id = row["id"] if row else 0

        return new_mem.id, audit_id

    # ─── AUDIT ────────────────────────────────────────────────────

    def get_audit_trail(self, memory_id: str) -> list[AuditEntry]:
        """Full audit history for a memory."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_audit_log WHERE memory_id = ? ORDER BY timestamp",
                (memory_id,),
            ).fetchall()

        return [
            AuditEntry(
                action=r["action"],
                actor=r["actor"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                details=json.loads(r["new_state"] or "{}"),
                reason=r["reason"] or "",
            )
            for r in rows
        ]

    def get_edges(self, memory_id: str) -> list[Relation]:
        """All edges involving a memory (as source or target)."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM memory_edges
                WHERE source_id = ? OR target_id = ?
                ORDER BY created_at
                """,
                (memory_id, memory_id),
            ).fetchall()

        return [
            Relation(
                type=EdgeType(r["edge_type"]),
                target_id=r["target_id"] if r["source_id"] == memory_id else r["source_id"],
                reason=r["reason"] or "",
                confidence=r["confidence"],
            )
            for r in rows
        ]

    def get_version_chain(self, memory_id: str) -> list[str]:
        """Walk parent_id links to build version chain."""
        chain: list[str] = []
        current = memory_id
        seen: set[str] = set()
        with self._conn() as conn:
            while current and current not in seen:
                seen.add(current)
                chain.append(current)
                row = conn.execute(
                    "SELECT parent_id FROM memories WHERE id = ?", (current,)
                ).fetchone()
                current = row["parent_id"] if row and row["parent_id"] else None

        chain.reverse()
        return chain

    # ─── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> Memory:
        """Convert a DB row to a Memory model."""
        return Memory(
            id=row["id"],
            content=row["content"],
            tags=json.loads(row["tags"]),
            namespace=Namespace(row["namespace"]),
            provenance=Provenance(
                source=SourceType(row["source"]),
                method=row["method"],
                author=row["author"],
                document_ref=row["document_ref"] or "",
            ),
            belief=Belief(
                confidence=row["confidence"],
                last_verified=datetime.fromisoformat(row["last_verified"]),
            ),
            freshness={
                "valid_from": datetime.fromisoformat(row["valid_from"]),
                "valid_until": datetime.fromisoformat(row["valid_until"])
                if row["valid_until"]
                else None,
                "is_canonical": bool(row["is_canonical"]),
            },
            version={
                "v": row["version"],
                "parent_id": row["parent_id"],
            },
            pii=bool(row["pii"]),
            meta=json.loads(row["meta"] or "{}"),
        )

    def count(self, *, canonical_only: bool = True) -> int:
        """Count memories in the store."""
        clause = "WHERE is_canonical = 1" if canonical_only else ""
        with self._conn() as conn:
            row = conn.execute(f"SELECT COUNT(*) as cnt FROM memories {clause}").fetchone()
            return row["cnt"] if row else 0
