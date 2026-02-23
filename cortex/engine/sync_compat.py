"""Sync compatibility mixin for CortexEngine.

Provides synchronous versions of core operations for CLI, sync callers,
and test utilities. Uses raw sqlite3 connections (not aiosqlite).
"""

from __future__ import annotations

import json
import logging
import sqlite3 as _sqlite3

import sqlite_vec

from cortex.temporal import now_iso

__all__ = ['SyncCompatMixin']

logger = logging.getLogger("cortex")


class SyncCompatMixin:
    """Synchronous compatibility layer for CortexEngine.

    These methods use a separate ``sqlite3.Connection`` (not aiosqlite)
    so they can be called from non-async contexts such as the CLI,
    ``cortex.sync.*`` modules, and test helpers.
    """

    # ─── Connection ─────────────────────────────────────────────

    def _get_sync_conn(self):
        """Get a raw sqlite3.Connection for sync callers."""
        if not hasattr(self, "_sync_conn") or self._sync_conn is None:
            from cortex.db import connect

            self._sync_conn = connect(str(self._db_path))
            try:
                self._sync_conn.enable_load_extension(True)
                sqlite_vec.load(self._sync_conn)
                self._sync_conn.enable_load_extension(False)
                self._vec_available = True
                logger.debug("sqlite-vec loaded successfully (sync)")
            except (OSError, AttributeError) as e:
                logger.debug("sqlite-vec extension not available (sync): %s", e)
                self._vec_available = False
        return self._sync_conn

    # ─── Init ───────────────────────────────────────────────────

    def init_db_sync(self) -> None:
        """Initialize database schema (sync version)."""
        from cortex.migrations.core import run_migrations
        from cortex.schema import ALL_SCHEMA

        conn = self._get_sync_conn()
        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available:
                continue
            conn.executescript(stmt)
        conn.commit()
        run_migrations(conn)
        from cortex.engine import get_init_meta

        for k, v in get_init_meta():
            conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (k, v),
            )
        conn.commit()
        logger.info("CORTEX database initialized (sync) at %s", self._db_path)

    # ─── Store ──────────────────────────────────────────────────

    def store_sync(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags=None,
        confidence: str = "stated",
        source=None,
        meta=None,
        valid_from=None,
        _skip_dedup: bool = False,
    ) -> int:
        """Store a fact synchronously (for sync callers like sync.read)."""
        if not project or not project.strip():
            raise ValueError("project cannot be empty")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        content = content.strip()

        # Gate 1: Minimum content length
        from cortex.facts.manager import FactManager

        min_len = FactManager.MIN_CONTENT_LENGTH
        if len(content) < min_len:
            raise ValueError(f"content too short ({len(content)} chars, min {min_len})")

        # Gate 2: Sanitize double-prefixed decisions
        if fact_type == "decision" and content.startswith("DECISION: DECISION:"):
            content = content.replace("DECISION: DECISION:", "DECISION:", 1)

        # Gate 3: Dedup — return existing ID if exact match exists
        conn = self._get_sync_conn()
        if not _skip_dedup:
            existing = conn.execute(
                "SELECT id FROM facts WHERE project = ? AND content = ? "
                "AND valid_until IS NULL LIMIT 1",
                (project, content),
            ).fetchone()
            if existing:
                logger.info("Dedup: fact already exists as #%d in %s", existing[0], project)
                return existing[0]

        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})
        cursor = conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags, confidence, "
            "valid_from, source, meta, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project, content, fact_type, tags_json, confidence, ts, source, meta_json, ts, ts),
        )
        fact_id = cursor.lastrowid
        if self._auto_embed and self._vec_available:
            try:
                embedding = self._get_embedder().embed(content)
                conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )
            except (_sqlite3.Error, OSError, ValueError) as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)
        conn.commit()

        # Log to ledger (sync)
        import hashlib

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        self._log_transaction_sync(
            conn, project, "store", {"fact_id": fact_id, "content_hash": content_hash}
        )

        # CDC: Encole for Neo4j sync
        conn.execute(
            "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
            (fact_id, "store_fact", "pending"),
        )
        conn.commit()

        # Graph extraction (sync)
        try:
            from cortex.graph import process_fact_graph_sync

            process_fact_graph_sync(conn, fact_id, content, project, ts)
            conn.commit()
        except (_sqlite3.Error, OSError, ValueError) as e:
            logger.warning("Graph extraction sync failed for fact %d: %s", fact_id, e)

        return fact_id

    # ─── Search ─────────────────────────────────────────────────

    def search_sync(
        self,
        query: str,
        project: str | None = None,
        top_k: int = 5,
    ) -> list:
        """Semantic vector search with text fallback (sync)."""
        from cortex.search_sync import (
            semantic_search_sync,
            text_search_sync,
        )

        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        conn = self._get_sync_conn()

        if self._vec_available:
            try:
                embedding = self._get_embedder().embed(query)
                results = semantic_search_sync(
                    conn,
                    embedding,
                    top_k=top_k,
                    project=project,
                )
                if results:
                    return results
            except (_sqlite3.Error, OSError, ValueError) as e:
                logger.warning("Semantic search sync failed: %s", e)

        return text_search_sync(conn, query, project=project, limit=top_k)

    def hybrid_search_sync(
        self,
        query: str,
        project: str | None = None,
        top_k: int = 10,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
    ) -> list:
        """Hybrid search combining semantic + text via RRF (sync)."""
        from cortex.search_sync import hybrid_search_sync, text_search_sync

        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        conn = self._get_sync_conn()

        if not self._vec_available:
            return text_search_sync(conn, query, project=project, limit=top_k)

        embedding = self._get_embedder().embed(query)
        return hybrid_search_sync(
            conn,
            query,
            embedding,
            top_k=top_k,
            project=project,
            vector_weight=vector_weight,
            text_weight=text_weight,
        )

    # ─── Graph ──────────────────────────────────────────────────

    def graph_sync(self, project: str | None = None, limit: int = 50) -> dict:
        """Retrieve the graph synchronously."""
        from cortex.graph.backends.sqlite import SQLiteBackend

        conn = self._get_sync_conn()
        return SQLiteBackend(conn).get_graph_sync(project=project, limit=limit)

    def query_entity_sync(self, name: str, project: str | None = None) -> dict | None:
        """Query an entity and its connections synchronously."""
        from cortex.graph.backends.sqlite import SQLiteBackend

        conn = self._get_sync_conn()
        return SQLiteBackend(conn).query_entity_sync(name=name, project=project)

    # ─── Cleanup ────────────────────────────────────────────────

    def close_sync(self):
        """Close sync connection."""
        if hasattr(self, "_sync_conn") and self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None
