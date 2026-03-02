"""
CORTEX v8 — L2 Hybrid Search Engine (Mem0-Killer).

Implements Reciprocal Rank Fusion (RRF) over the L2 vector database
(SovereignVectorStoreL2 — facts_meta + vec_facts + facts_meta_fts).

Unlike the main hybrid search (cortex.search.hybrid), which operates on the
primary `facts` table via aiosqlite, this engine operates directly on the
L2 sync SQLite connection (sqlite3) that lives inside SovereignVectorStoreL2.

Architecture:
    ┌──────────────────────────────────────────────────┐
    │  L2 Hybrid Search                                │
    │                                                  │
    │  Query ──┬─→ Vector KNN (vec0/sqlite-vec)    ─┐  │
    │          └─→ FTS5 BM25 (facts_meta_fts)     ─┤  │
    │                                              ↓  │
    │                          RRF Fusion (k=60)      │
    │                                              ↓  │
    │                         Ranked L2 Results        │
    └──────────────────────────────────────────────────┘

Key design decisions:
  - RRF_K=60 — same constant as main hybrid for consistency
  - FTS5 mirror table (`facts_meta_fts`) is created lazily on first
    call to `ensure_fts_table()` — zero migration friction
  - UUID Trick: results carry a sequential `rank_index` (0,1,2...) for
    clean LLM context injection without exposing internal UUIDs
  - Thread safety: sync lock inherited from parent store's asyncio.Lock

Derivation: Ω₁ (Multi-Scale Causality) + Ω₂ (Entropic Asymmetry)
DECISION: Operate on L2's sync conn to avoid aiosqlite overhead for
         hot-path recall queries. asyncio.to_thread wraps at call site.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

import numpy as np

__all__ = ["L2HybridSearch", "L2SearchResult"]

logger = logging.getLogger("cortex.memory.l2_hybrid_search")

# ─── Constants ────────────────────────────────────────────────────────────────
RRF_K: Final[int] = 60
DEFAULT_VECTOR_WEIGHT: Final[float] = 0.6
DEFAULT_TEXT_WEIGHT: Final[float] = 0.4
FTS_TABLE: Final[str] = "facts_meta_fts"
META_TABLE: Final[str] = "facts_meta"
VEC_TABLE: Final[str] = "vec_facts"


# ─── Result Model ─────────────────────────────────────────────────────────────


@dataclass
class L2SearchResult:
    """A single L2 hybrid search result.

    The `rank_index` field provides a clean 0-based sequential identifier
    safe for LLM context injection (UUID Trick — avoids raw UUID confusion).
    """

    rank_index: int
    internal_id: str           # The real UUID from facts_meta
    tenant_id: str
    project_id: str
    content: str
    timestamp: float
    is_diamond: bool
    is_bridge: bool
    confidence: str
    cognitive_layer: str
    rrf_score: float
    source_signals: list[str]  # ["vector", "fts"] — which branches contributed
    metadata: dict = field(default_factory=dict)

    def to_context_dict(self) -> dict:
        """Serialize for LLM injection. Uses rank_index, never raw UUIDs."""
        return {
            "idx": self.rank_index,           # Clean index for LLM referencing
            "content": self.content,
            "project": self.project_id,
            "layer": self.cognitive_layer,
            "score": round(self.rrf_score, 6),
            "signals": self.source_signals,
            "diamond": self.is_diamond,
        }


# ─── FTS Query Sanitizer ───────────────────────────────────────────────────────

_FTS_UNSAFE = re.compile(r'["\(\)\*\:\^~\[\]\{\}\\]')


def _sanitize_fts_query(query: str) -> str:
    """Sanitize a raw query into a safe FTS5 MATCH expression.

    Strategy: strip unsafe chars, then join non-empty tokens with implicit AND.
    Single-token queries become prefix searches (token*) for fuzzy recall.
    """
    cleaned = _FTS_UNSAFE.sub(" ", query).strip()
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
    if not tokens:
        return '""'

    if len(tokens) == 1:
        return f'"{tokens[0]}"*'

    return " AND ".join(f'"{t}"' for t in tokens)


# ─── L2 Hybrid Search Engine ──────────────────────────────────────────────────


class L2HybridSearch:
    """Hybrid Search engine operating on SovereignVectorStoreL2's sync connection.

    This class augments L2 with an FTS5 mirror table and implements RRF fusion
    between vector KNN results and BM25 text results.

    Usage:
        store = SovereignVectorStoreL2(...)
        engine = L2HybridSearch(store)
        await engine.ensure_fts_table()  # one-time setup

        results = await engine.search(
            query="¿Qué coche tiene Borja?",
            query_embedding=embedding_vector,
            tenant_id="borja",
            project_id="personal",
            top_k=5,
        )
    """

    __slots__ = ("_store",)

    def __init__(self, store: SovereignVectorStoreL2) -> None:
        self._store = store

    # ─── Schema Bootstrap ─────────────────────────────────────────────────────

    def ensure_fts_table(self) -> None:
        """Create FTS5 mirror table for facts_meta if not present.

        Creates:
            - `facts_meta_fts`: FTS5 virtual table mirroring `content` + `id`
            - Triggers to keep mirror in sync with facts_meta inserts/deletes/updates

        Safe to call multiple times (idempotent).
        """
        conn = self._store._get_conn()
        try:
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5(
                    content,
                    id UNINDEXED,
                    tokenize='unicode61 remove_diacritics 2'
                )
            """)

            # Insert trigger — populate FTS on new facts_meta rows
            conn.execute(f"""
                CREATE TRIGGER IF NOT EXISTS facts_meta_fts_insert
                AFTER INSERT ON {META_TABLE}
                BEGIN
                    INSERT INTO {FTS_TABLE}(rowid, content, id)
                    VALUES (NEW.rowid, NEW.content, NEW.id);
                END
            """)

            # Delete trigger — remove FTS entries when facts_meta row deleted
            conn.execute(f"""
                CREATE TRIGGER IF NOT EXISTS facts_meta_fts_delete
                AFTER DELETE ON {META_TABLE}
                BEGIN
                    DELETE FROM {FTS_TABLE} WHERE rowid = OLD.rowid;
                END
            """)

            # Update trigger — refresh FTS when content changes
            conn.execute(f"""
                CREATE TRIGGER IF NOT EXISTS facts_meta_fts_update
                AFTER UPDATE OF content ON {META_TABLE}
                BEGIN
                    DELETE FROM {FTS_TABLE} WHERE rowid = OLD.rowid;
                    INSERT INTO {FTS_TABLE}(rowid, content, id)
                    VALUES (NEW.rowid, NEW.content, NEW.id);
                END
            """)

            # Backfill: populate FTS for any pre-existing rows
            conn.execute(f"""
                INSERT OR IGNORE INTO {FTS_TABLE}(rowid, content, id)
                SELECT rowid, content, id FROM {META_TABLE}
                WHERE content IS NOT NULL
            """)

            conn.commit()
            logger.info("L2HybridSearch: FTS5 mirror table '%s' ensured.", FTS_TABLE)

        except sqlite3.Error as e:
            conn.rollback()
            logger.error("L2HybridSearch: FTS5 table setup failed: %s", e)
            raise

    # ─── Branch: Vector KNN ───────────────────────────────────────────────────

    def _vector_search(
        self,
        conn: sqlite3.Connection,
        query_embedding: list[float],
        tenant_id: str,
        project_id: str,
        top_k: int,
    ) -> list[tuple[str, int]]:  # (id, rank_0_indexed)
        """Execute ANN vector search on vec_facts.

        Returns list of (facts_meta.id, 0-based rank).
        """
        embedding_bytes = np.array(query_embedding, dtype=np.float32).tobytes()

        # Inner KNN: get rowids from vec0, then join to tenant-filtered facts_meta
        sql = f"""
            SELECT m.id, v.distance
            FROM {VEC_TABLE} v
            JOIN {META_TABLE} m ON m.rowid = v.rowid
            WHERE v.embedding MATCH ?
              AND k = ?
              AND m.tenant_id = ?
              AND (m.project_id = ? OR m.is_bridge = 1)
            ORDER BY v.distance ASC
            LIMIT ?
        """
        try:
            cursor = conn.execute(sql, (embedding_bytes, top_k * 3, tenant_id, project_id, top_k))
            rows = cursor.fetchall()
            return [(row[0], idx) for idx, row in enumerate(rows)]
        except sqlite3.Error as e:
            logger.error("L2HybridSearch: Vector branch failed: %s", e)
            return []

    # ─── Branch: FTS5 BM25 ────────────────────────────────────────────────────

    def _fts_search(
        self,
        conn: sqlite3.Connection,
        query: str,
        tenant_id: str,
        project_id: str,
        top_k: int,
    ) -> list[tuple[str, int]]:  # (id, rank_0_indexed)
        """Execute FTS5 BM25 search on facts_meta_fts.

        Returns list of (facts_meta.id, 0-based rank).
        """
        fts_query = _sanitize_fts_query(query)

        sql = f"""
            SELECT m.id, bm25({FTS_TABLE}) AS bm25_rank
            FROM {FTS_TABLE} fts
            JOIN {META_TABLE} m ON m.rowid = fts.rowid
            WHERE fts.content MATCH ?
              AND m.tenant_id = ?
              AND (m.project_id = ? OR m.is_bridge = 1)
            ORDER BY bm25_rank ASC
            LIMIT ?
        """
        try:
            cursor = conn.execute(sql, (fts_query, tenant_id, project_id, top_k))
            rows = cursor.fetchall()
            return [(row[0], idx) for idx, row in enumerate(rows)]
        except sqlite3.Error as e:
            logger.warning("L2HybridSearch: FTS5 branch failed (table may not exist): %s", e)
            return []

    # ─── RRF Fusion ───────────────────────────────────────────────────────────

    @staticmethod
    def _rrf_fuse(
        vector_results: list[tuple[str, int]],
        fts_results: list[tuple[str, int]],
        vector_weight: float,
        text_weight: float,
        top_k: int,
    ) -> list[tuple[str, float, list[str]]]:  # (id, rrf_score, signals)
        """Reciprocal Rank Fusion with weighted contributions.

        Score formula: Σ weight / (k + rank)
        Returns top_k results sorted by descending RRF score.
        """
        total_w = vector_weight + text_weight
        w_vec = vector_weight / total_w
        w_txt = text_weight / total_w

        rrf_scores: dict[str, float] = {}
        signals: dict[str, list[str]] = {}

        for fact_id, rank in vector_results:
            score = w_vec / (RRF_K + rank + 1)
            rrf_scores[fact_id] = rrf_scores.get(fact_id, 0.0) + score
            signals.setdefault(fact_id, []).append("vector")

        for fact_id, rank in fts_results:
            score = w_txt / (RRF_K + rank + 1)
            rrf_scores[fact_id] = rrf_scores.get(fact_id, 0.0) + score
            if "fts" not in signals.get(fact_id, []):
                signals.setdefault(fact_id, []).append("fts")

        sorted_ids = sorted(rrf_scores, key=lambda fid: rrf_scores[fid], reverse=True)[:top_k]
        return [(fid, rrf_scores[fid], signals.get(fid, [])) for fid in sorted_ids]

    # ─── Result Hydration ─────────────────────────────────────────────────────

    def _hydrate(
        self,
        conn: sqlite3.Connection,
        fused: list[tuple[str, float, list[str]]],
    ) -> list[L2SearchResult]:
        """Fetch full row data for RRF winners. UUID Trick applied here."""
        if not fused:
            return []

        placeholders = ",".join("?" * len(fused))
        id_index = {item[0]: item for item in fused}

        try:
            cursor = conn.execute(
                f"""
                SELECT id, tenant_id, project_id, content, timestamp,
                       is_diamond, is_bridge, confidence, cognitive_layer, metadata
                FROM {META_TABLE}
                WHERE id IN ({placeholders})
                """,
                [item[0] for item in fused],
            )
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error("L2HybridSearch: Hydration query failed: %s", e)
            return []

        import json

        results: list[L2SearchResult] = []
        for rank_index, row in enumerate(rows):
            fact_id = row[0]
            _, rrf_score, source_signals = id_index.get(fact_id, (fact_id, 0.0, []))

            try:
                meta = json.loads(row[9]) if row[9] else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}

            results.append(
                L2SearchResult(
                    rank_index=rank_index,          # UUID Trick: clean 0-based index
                    internal_id=fact_id,
                    tenant_id=row[1],
                    project_id=row[2],
                    content=row[3] or "",
                    timestamp=float(row[4] or 0.0),
                    is_diamond=bool(row[5]),
                    is_bridge=bool(row[6]),
                    confidence=row[7] or "C3",
                    cognitive_layer=row[8] or "semantic",
                    rrf_score=rrf_score,
                    source_signals=source_signals,
                    metadata=meta,
                )
            )

        # Re-sort by RRF score (DB order may differ from fusion order)
        results.sort(key=lambda r: r.rrf_score, reverse=True)
        # Re-assign rank_index after sort
        for i, r in enumerate(results):
            object.__setattr__(r, "rank_index", i) if hasattr(r, "__setattr__") else None
            r.rank_index = i

        return results

    # ─── Public API ───────────────────────────────────────────────────────────

    def search_sync(
        self,
        query: str,
        query_embedding: list[float],
        tenant_id: str = "default",
        project_id: str = "default",
        top_k: int = 5,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        text_weight: float = DEFAULT_TEXT_WEIGHT,
    ) -> list[L2SearchResult]:
        """Execute L2 Hybrid RRF search (sync).

        Dispatches vector KNN and FTS5 BM25 in sequence (sync conn),
        fuses with RRF, and returns hydrated results with UUID Trick applied.

        Args:
            query: Natural language query string.
            query_embedding: Pre-computed embedding vector for the query.
            tenant_id: Partition key for multi-tenancy.
            project_id: Project partition key.
            top_k: Number of results to return.
            vector_weight: Weight for vector branch (default 0.6).
            text_weight: Weight for FTS5 branch (default 0.4).

        Returns:
            List of L2SearchResult sorted by descending RRF score.
        """
        conn = self._store._get_conn()
        fetch_k = top_k * 2  # Overfetch for RRF overlap

        vec_results = self._vector_search(conn, query_embedding, tenant_id, project_id, fetch_k)
        fts_results = self._fts_search(conn, query, tenant_id, project_id, fetch_k)

        if not vec_results and not fts_results:
            logger.debug("L2HybridSearch: Both branches returned empty for query='%s'", query[:50])
            return []

        fused = self._rrf_fuse(vec_results, fts_results, vector_weight, text_weight, top_k)
        results = self._hydrate(conn, fused)

        logger.debug(
            "L2HybridSearch: query='%s' → vec=%d fts=%d fused=%d",
            query[:40],
            len(vec_results),
            len(fts_results),
            len(results),
        )
        return results

    async def search(
        self,
        query: str,
        query_embedding: list[float],
        tenant_id: str = "default",
        project_id: str = "default",
        top_k: int = 5,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        text_weight: float = DEFAULT_TEXT_WEIGHT,
    ) -> list[L2SearchResult]:
        """Async wrapper for search_sync. Offloads to thread pool.

        The L2 store uses a sync sqlite3 connection. We push to a thread
        to never block the async event loop (Ω₂: zero blocking I/O).
        """
        import asyncio

        return await asyncio.to_thread(
            self.search_sync,
            query=query,
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            project_id=project_id,
            top_k=top_k,
            vector_weight=vector_weight,
            text_weight=text_weight,
        )
