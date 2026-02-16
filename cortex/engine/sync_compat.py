"""Sync compatibility mixin for CortexEngine.

Provides synchronous versions of core operations for CLI, sync callers,
and test utilities. Uses raw sqlite3 connections (not aiosqlite).
"""
from __future__ import annotations

import json
import logging
import sqlite3 as _sqlite3
from typing import Optional

import sqlite_vec

from cortex.temporal import now_iso

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
            self._sync_conn = _sqlite3.connect(
                str(self._db_path), timeout=30, check_same_thread=False,
            )
            self._sync_conn.execute("PRAGMA journal_mode=WAL")
            self._sync_conn.execute("PRAGMA synchronous=NORMAL")
            self._sync_conn.execute("PRAGMA foreign_keys=ON")
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
        from cortex.schema import ALL_SCHEMA
        from cortex.migrations.core import run_migrations

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
    ) -> int:
        """Store a fact synchronously (for sync callers like sync.read)."""
        conn = self._get_sync_conn()
        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})
        cursor = conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags, confidence, "
            "valid_from, source, meta, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project, content, fact_type, tags_json, confidence,
             ts, source, meta_json, ts, ts),
        )
        fact_id = cursor.lastrowid
        if self._auto_embed and self._vec_available:
            try:
                embedding = self._get_embedder().embed(content)
                conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) "
                    "VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )
            except Exception as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)
        conn.commit()
        return fact_id

    # ─── Search ─────────────────────────────────────────────────

    def search_sync(
        self,
        query: str,
        project: Optional[str] = None,
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
                    conn, embedding, top_k=top_k, project=project,
                )
                if results:
                    return results
            except Exception as e:
                logger.warning("Semantic search sync failed: %s", e)

        return text_search_sync(conn, query, project=project, limit=top_k)

    def hybrid_search_sync(
        self,
        query: str,
        project: Optional[str] = None,
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
            conn, query, embedding,
            top_k=top_k, project=project,
            vector_weight=vector_weight,
            text_weight=text_weight,
        )

    # ─── Consensus ──────────────────────────────────────────────

    def vote_sync(self, fact_id: int, agent: str, value: int) -> float:
        """Cast a v1 consensus vote synchronously.

        Args:
            fact_id: The fact to vote on.
            agent: Agent name.
            value: Vote value (-1, 0, or 1).

        Returns:
            Updated consensus score.
        """
        if value not in (-1, 0, 1):
            raise ValueError(f"vote value must be -1, 0, or 1, got {value}")
        conn = self._get_sync_conn()
        if value == 0:
            conn.execute(
                "DELETE FROM consensus_votes WHERE fact_id = ? AND agent = ?",
                (fact_id, agent),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO consensus_votes "
                "(fact_id, agent, vote) VALUES (?, ?, ?)",
                (fact_id, agent, value),
            )
        # Recalculate consensus score
        row = conn.execute(
            "SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?",
            (fact_id,),
        ).fetchone()
        vote_sum = row[0] or 0
        score = max(0.0, 1.0 + (vote_sum * 0.1))
        if score >= 1.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'verified' "
                "WHERE id = ?",
                (score, fact_id),
            )
        elif score <= 0.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'disputed' "
                "WHERE id = ?",
                (score, fact_id),
            )
        else:
            conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )
        conn.commit()
        return score

    # ─── Cleanup ────────────────────────────────────────────────

    def close_sync(self):
        """Close sync connection."""
        if hasattr(self, "_sync_conn") and self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None
