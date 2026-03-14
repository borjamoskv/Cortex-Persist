"""
CORTEX v6 — Sovereign Vector Store (SQLite-Vec).

Zero-Trust, Multi-Tenant Semantic Memory backed by sqlite-vec.
Enforces partition by tenant_id and incorporates OUROBOROS success_rate
and temporal decay directly in the embedding retrieval.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from pathlib import Path

import numpy as np

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.models import CortexFactModel

__all__ = ["SovereignVectorStoreL2"]

# Lazy imports to avoid circular deps at module load
# L2HybridSearch and PIISanitizer only needed at runtime
_L2_HYBRID_SEARCH_AVAILABLE: bool | None = None  # None = not yet checked

logger = logging.getLogger("cortex.memory.sqlite_vec_store")


def cortex_decay(is_diamond: int, timestamp: float, current_time: float, half_life: float) -> float:
    """Calcula el decaimiento temporal soberano."""
    if is_diamond:
        return 1.0
    age = max(0.0, current_time - timestamp)
    return float(0.5 ** (age / half_life))


class SovereignVectorStoreL2:
    """Async vector store for CORTEX v6 L2 semantic memory.

    Uses `sqlite-vec` for extremely fast, local, zero-trust vector recall.
    Calculates final scores based on Cosine Similarity, Temporal Decay,
    and OUROBOROS success_rate.
    """

    __slots__ = (
        "_db_path",
        "_encoder",
        "_conn",
        "_lock",
        "_ready",
        "_half_life",
        "_hybrid",
        "_sanitizer",
    )

    MAX_DOMAIN_ENTROPY = 5000  # Axiom Ω8: Critical mass for Universe Splitting

    def __init__(
        self,
        encoder: AsyncEncoder,
        db_path: str | Path = "~/.cortex/vectors.db",
        half_life_days: int = 7,
    ) -> None:
        self._encoder = encoder
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()
        self._ready = False
        self._half_life = half_life_days * 24 * 3600
        # Lazy-initialized subsystems
        self._hybrid = None  # L2HybridSearch — created after conn is ready
        self._sanitizer = None  # PIISanitizer singleton

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if sqlite_vec is None:
                err = "sqlite_vec module not installed. Run 'pip install sqlite-vec'"
                raise RuntimeError(err)

            self._conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=5.0,  # opening-policy: O(1) fail-fast
            )
            # runtime-policy: wait up to 5s for WAL write-lock contention (Axiom Ω6)
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.row_factory = sqlite3.Row

            # Register Sovereign Functions
            self._conn.create_function("cortex_decay", 4, cortex_decay)

            # Initialization
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS facts_meta (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    content TEXT,
                    timestamp REAL,
                    is_diamond INTEGER,
                    is_bridge INTEGER,
                    confidence TEXT,
                    success_rate REAL,
                    cognitive_layer TEXT,
                    parent_decision_id TEXT,
                    metadata TEXT
                )
            """)
            self._conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
                    embedding float[{self._encoder.dimension}]
                )
            """)

            # Indexes for Zero-Trust and Speed
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tenant_proj ON facts_meta(tenant_id, project_id)"
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_bridge ON facts_meta(is_bridge)")

            self._ready = True

            # Ω₀: Structural integrity migration
            try:
                self._conn.execute("ALTER TABLE facts_meta ADD COLUMN cognitive_layer TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._conn.execute("ALTER TABLE facts_meta ADD COLUMN parent_decision_id TEXT")
            except sqlite3.OperationalError:
                pass
            self._conn.commit()

        # Initialize L2HybridSearch (FTS5 mirror) after conn is established
        if self._hybrid is None:
            try:
                from cortex.memory.l2_hybrid_search import L2HybridSearch

                self._hybrid = L2HybridSearch(self)
                self._hybrid.ensure_fts_table()
            except Exception as e:  # noqa: BLE001
                logger.warning("L2HybridSearch init failed (FTS5 unavailable): %s", e)
                self._hybrid = None

        return self._conn

    @property
    def hybrid_search(self):
        """Access the L2HybridSearch engine (None if FTS5 unavailable)."""
        return self._hybrid

    def _get_sanitizer(self):
        """Return the module-level PIISanitizer singleton."""
        if self._sanitizer is None:
            try:
                from cortex.memory.pii_sanitizer import get_pii_sanitizer

                self._sanitizer = get_pii_sanitizer()
            except ImportError:
                pass
        return self._sanitizer

    def _get_domain_tables(self, conn: sqlite3.Connection, tenant_id: str, project_id: str) -> tuple[str, str]:
        """Axiom Ω8: Vertical Domain Cut. 
        If a corpus weighs too much, we split the universe and migrate only distilled axioms.
        """
        safe_tenant = "".join(c for c in tenant_id if c.isalnum() or c == "_")
        safe_proj = "".join(c for c in project_id if c.isalnum() or c == "_")
        if not safe_tenant or not safe_proj:
            return "facts_meta", "vec_facts"

        meta_tb = f"facts_meta_{safe_tenant}_{safe_proj}"
        vec_tb = f"vec_facts_{safe_tenant}_{safe_proj}"

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (meta_tb,))
        if cursor.fetchone():
            return meta_tb, vec_tb

        cursor.execute(
            "SELECT count(1) FROM facts_meta WHERE tenant_id = ? AND project_id = ?",
            (tenant_id, project_id)
        )
        count = cursor.fetchone()[0]

        if count >= self.MAX_DOMAIN_ENTROPY:
            logger.warning(
                "🌌 [UNIVERSE SPLIT] Domain %s/%s reached mass %d. Sharding vector space.", 
                tenant_id, project_id, count
            )
            # Create sharded schema
            conn.execute(f"""
                CREATE TABLE {meta_tb} (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    content TEXT,
                    timestamp REAL,
                    is_diamond INTEGER,
                    is_bridge INTEGER,
                    confidence TEXT,
                    success_rate REAL,
                    cognitive_layer TEXT,
                    parent_decision_id TEXT,
                    metadata TEXT
                )
            """)
            conn.execute(
                f"CREATE VIRTUAL TABLE {vec_tb} USING "
                f"vec0(embedding float[{self._encoder.dimension}])"
            )

            # Migrate only distilled axioms (is_diamond = 1)
            conn.execute(f"""
                INSERT INTO {meta_tb} (
                    rowid, id, tenant_id, project_id, content, timestamp,
                    is_diamond, is_bridge, confidence, success_rate,
                    cognitive_layer, parent_decision_id, metadata
                )
                SELECT
                    rowid, id, tenant_id, project_id, content, timestamp,
                    is_diamond, is_bridge, confidence, success_rate,
                    cognitive_layer, parent_decision_id, metadata
                FROM facts_meta
                WHERE tenant_id = ? AND project_id = ? AND is_diamond = 1
            """, (tenant_id, project_id))

            conn.execute(f"""
                INSERT INTO {vec_tb}(rowid, embedding)
                SELECT v.rowid, v.embedding
                FROM vec_facts v
                JOIN facts_meta m ON v.rowid = m.rowid
                WHERE m.tenant_id = ? AND m.project_id = ? AND m.is_diamond = 1
            """, (tenant_id, project_id))

            conn.execute(
                f"CREATE INDEX idx_tenant_proj_{safe_tenant}_{safe_proj} "
                f"ON {meta_tb}(tenant_id, project_id)"
            )
            conn.execute(
                f"CREATE INDEX idx_bridge_{safe_tenant}_{safe_proj} "
                f"ON {meta_tb}(is_bridge)"
            )
            
            conn.commit()
            return meta_tb, vec_tb

        return "facts_meta", "vec_facts"

    async def memorize(self, fact: CortexFactModel) -> None:
        """Encode and store a multi-tenant CortexFactModel.

        Applies PII sanitization to content before storage if a sanitizer
        is available. The sanitized content is stored and vectorized;
        encrypted PII fragments are persisted in the metadata field.
        """
        conn = self._get_conn()

        # ─── PII Sanitization Gate (Moved outside the DB Lock) ────────
        sanitized_content = fact.content
        sanitized_meta = dict(fact.metadata) if fact.metadata else {}

        sanitizer = self._get_sanitizer()
        if sanitizer and fact.content:
            # We use to_thread because complex Regex or NLP blocks the event loop
            report = await asyncio.to_thread(
                sanitizer.sanitize, fact.content, tenant_id=fact.tenant_id
            )
            if report.has_pii:
                sanitized_content = report.sanitized
                if report.encrypted_fragments:
                    sanitized_meta["_pii_fragments"] = report.encrypted_fragments
                    sanitized_meta["_pii_categories"] = [c.value for c in report.pii_categories]
                logger.info(
                    "PII detected in fact [%s] for tenant %s — %d fragments encrypted.",
                    fact.id,
                    fact.tenant_id,
                    len(report.encrypted_fragments),
                )
        # ──────────────────────────────────────────────────────────────

        async with self._lock:
            embedding_bytes = np.array(fact.embedding, dtype=np.float32).tobytes()

            cursor = conn.cursor()
            try:
                meta_tb, vec_tb = self._get_domain_tables(conn, fact.tenant_id, fact.project_id)
                cursor.execute(
                    f"""
                    INSERT INTO {meta_tb} (
                        id, tenant_id, project_id, content, timestamp,
                        is_diamond, is_bridge, confidence, success_rate,
                        cognitive_layer, parent_decision_id, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fact.id,
                        fact.tenant_id,
                        fact.project_id,
                        sanitized_content,  # PII-sanitized content
                        fact.timestamp,
                        int(fact.is_diamond),
                        int(fact.is_bridge),
                        fact.confidence,
                        fact.success_rate,
                        fact.cognitive_layer,
                        fact.parent_decision_id,
                        json.dumps(sanitized_meta),  # Includes PII encrypted fragments
                    ),
                )
                rowid = cursor.lastrowid

                cursor.execute(
                    f"INSERT INTO {vec_tb}(rowid, embedding) VALUES (?, ?)",
                    (rowid, embedding_bytes),
                )
                conn.commit()
            except (sqlite3.Error, RuntimeError) as e:
                # LEGION-OMEGA (Chronos Sniper): Prevent DB from entering corrupt
                # transaction state after error.
                conn.rollback()
                logger.error(
                    "SovereignVectorStoreL2: Database integrity breach during memorize: %s",
                    e,
                )
                raise

    async def recall_secure(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
        layer: str | None = None,
    ) -> list[CortexFactModel]:
        """[C5] Recuperación particionada Zero-Trust con ranking SQL nativo."""
        conn = self._get_conn()
        query_vector = await self._encoder.encode(query)
        embedding_bytes = np.array(query_vector, dtype=np.float32).tobytes()
        now = time.time()

        # Vector search + Reranking in SQL
        cursor = conn.cursor()
        meta_tb, vec_tb = self._get_domain_tables(conn, tenant_id, project_id)

        sql = f"""
            SELECT
                m.rowid, m.id, m.tenant_id, m.project_id, m.content, m.timestamp,
                m.is_diamond, m.is_bridge, m.confidence, m.success_rate,
                m.cognitive_layer, m.parent_decision_id, m.metadata,
                v.embedding,
                ((1.0 - vec_distance_cosine(v.embedding, ?) / 2.0) *
                 cortex_decay(m.is_diamond, m.timestamp, ?, ?) *
                 m.success_rate) as final_score
            FROM {meta_tb} m
            JOIN {vec_tb} v ON m.rowid = v.rowid
            WHERE m.tenant_id = ? AND (m.project_id = ? OR m.is_bridge = 1)
        """
        params = [embedding_bytes, now, self._half_life, tenant_id, project_id]

        if layer:
            sql += " AND m.cognitive_layer = ?"
            params.append(layer)

        sql += " ORDER BY final_score DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, tuple(params))

        rows = cursor.fetchall()
        final_facts = []

        for row in rows:
            score = row["final_score"]

            # LEGION-OMEGA (Entropy Demon): N+1 Subquery actually eliminated.
            emb_bytes = row["embedding"]
            emb = np.frombuffer(emb_bytes, dtype=np.float32).tolist() if emb_bytes else []

            fact = CortexFactModel(
                id=row["id"],
                tenant_id=row["tenant_id"],
                project_id=row["project_id"],
                content=row["content"],
                embedding=emb,
                timestamp=row["timestamp"],
                is_diamond=bool(row["is_diamond"]),
                is_bridge=bool(row["is_bridge"]),
                confidence=row["confidence"],
                cognitive_layer=row["cognitive_layer"] or "semantic",
                parent_decision_id=row["parent_decision_id"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
            object.__setattr__(fact, "_recall_score", score)
            final_facts.append(fact)

        return final_facts

    async def recall(
        self,
        query: str,
        limit: int = 5,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list[CortexFactModel]:
        """Backward-compatible recall for legacy callers. Maps to recall_secure."""
        return await self.recall_secure(
            tenant_id=tenant_id, project_id=project or "default", query=query, limit=limit
        )

    async def recall_hybrid(
        self,
        query: str,
        query_embedding: list[float],
        tenant_id: str = "default",
        project_id: str = "default",
        limit: int = 5,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
    ):
        """L2 Hybrid Search: Vector KNN + FTS5 BM25 fused via RRF.

        This is the Mem0-Killer endpoint. Returns L2SearchResult objects
        with clean rank_index (UUID Trick) for safe LLM context injection.

        Falls back to pure vector recall if L2HybridSearch is unavailable.
        """
        if self._hybrid is not None:
            return await self._hybrid.search(
                query=query,
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                project_id=project_id,
                top_k=limit,
                vector_weight=vector_weight,
                text_weight=text_weight,
            )

        # Fallback: pure semantic recall
        logger.warning("recall_hybrid: L2HybridSearch unavailable — falling back to recall_secure")
        return await self.recall_secure(
            tenant_id=tenant_id,
            project_id=project_id,
            query=query,
            limit=limit,
        )

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                self._ready = False
