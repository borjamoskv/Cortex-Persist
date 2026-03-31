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
from typing import Any, Optional

import numpy as np

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

from cortex.guards.exergy_guard import calculate_exergy
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.models import CortexFactModel
from cortex.utils import void_vec
from cortex.utils.turboquant import encode_query_qjl, optimize_vector_qjl

__all__ = ["SovereignVectorStoreL2"]

# Lazy imports to avoid circular deps at module load
# L2HybridSearch and PIISanitizer only needed at runtime
_L2_HYBRID_SEARCH_AVAILABLE: Optional[bool] = None  # None = not yet checked

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
        "_vector_enabled",
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
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
        self._ready = False
        self._half_life = half_life_days * 24 * 3600
        self._vector_enabled = False
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
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA busy_timeout=5000")

            try:
                self._conn.enable_load_extension(True)
                sqlite_vec.load(self._conn)
                self._vector_enabled = True
                logger.info("✅ [VECTORS] sqlite-vec extension loaded successfully.")
            except (AttributeError, sqlite3.OperationalError, Exception) as e:
                logger.warning(
                    "⚠️ [VECTORS] Fallback Mode ACTIVE: Could not load sqlite-vec: %s. "
                    "Semantic search will be disabled but metadata storage is preserved.",
                    e,
                )
                self._vector_enabled = False

            self._conn.row_factory = sqlite3.Row

            # Register Sovereign Functions
            self._conn.create_function("cortex_decay", 4, cortex_decay)
            self._conn.create_function("cortex_exergy", 1, calculate_exergy)
            self._conn.create_function("void_dist", 2, void_vec.void_hamming_dist)

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
                    metadata TEXT,
                    -- Double-Plane Facets (Ω₁₃)
                    category TEXT DEFAULT 'general',
                    quadrant TEXT DEFAULT 'ACTIVE',
                    storage_tier TEXT DEFAULT 'HOT',
                    facet_version INTEGER DEFAULT 2,
                    exergy_score REAL DEFAULT 1.0
                )
            """)
            if self._vector_enabled:
                self._conn.executescript(
                    f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
                        embedding int8[{self._encoder.dimension}]
                    );
                    CREATE TABLE IF NOT EXISTS vec_void (
                        rowid INTEGER PRIMARY KEY,
                        embedding BLOB
                    );
                    CREATE TABLE IF NOT EXISTS vec_void_mih (
                        rowid INTEGER PRIMARY KEY,
                        s0 INTEGER, s1 INTEGER, s2 INTEGER, s3 INTEGER,
                        s4 INTEGER, s5 INTEGER, s6 INTEGER, s7 INTEGER,
                        s8 INTEGER, s9 INTEGER, s10 INTEGER, s11 INTEGER,
                        s12 INTEGER, s13 INTEGER, s14 INTEGER, s15 INTEGER
                    );
                    """
                )
                for i in range(16):
                    self._conn.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_void_mih_s{i} ON vec_void_mih(s{i})"
                    )

            # Indexes for Zero-Trust and Speed
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tenant_proj ON facts_meta(tenant_id, project_id)"
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_bridge ON facts_meta(is_bridge)")

            self._ready = True

            # Ω₀: Structural integrity migration
            migrations = [
                ("cognitive_layer", "TEXT"),
                ("parent_decision_id", "TEXT"),
                ("category", "TEXT DEFAULT 'general'"),
                ("quadrant", "TEXT DEFAULT 'ACTIVE'"),
                ("storage_tier", "TEXT DEFAULT 'HOT'"),
                ("facet_version", "INTEGER DEFAULT 2"),
                ("exergy_score", "REAL DEFAULT 1.0"),
            ]

            cursor = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'facts_meta%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for tb in tables:
                for col, col_type in migrations:
                    # Validate col strictly to prevent SQL injection.
                    if not all(c.isalnum() or c == "_" for c in col):
                        continue
                    try:
                        alter_query = f"ALTER TABLE {tb} ADD COLUMN {col} {col_type}"
                        self._conn.execute(alter_query)  # nosec B608
                    except sqlite3.OperationalError:
                        pass  # Column already exists
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

    def _get_domain_tables(
        self, conn: sqlite3.Connection, tenant_id: str, project_id: str
    ) -> tuple[str, str, str | None]:
        """Axiom Ω8: Vertical Domain Cut.
        If a corpus weighs too much, we split the universe and migrate only distilled axioms.
        """
        safe_tenant = "".join(c for c in tenant_id if c.isalnum() or c == "_")
        safe_proj = "".join(c for c in project_id if c.isalnum() or c == "_")
        if not safe_tenant or not safe_proj:
            return "facts_meta", "vec_facts", "vec_void"

        meta_tb = f"facts_meta_{safe_tenant}_{safe_proj}"
        vec_tb = f"vec_facts_{safe_tenant}_{safe_proj}"
        vec_void_tb = f"vec_void_{safe_tenant}_{safe_proj}"

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (meta_tb,))
        if cursor.fetchone():
            return meta_tb, vec_tb, vec_void_tb

        cursor.execute(
            "SELECT count(1) FROM facts_meta WHERE tenant_id = ? AND project_id = ?",
            (tenant_id, project_id),
        )
        count = cursor.fetchone()[0]

        if count >= self.MAX_DOMAIN_ENTROPY:
            logger.warning(
                "🌌 [UNIVERSE SPLIT] Domain %s/%s reached mass %d. Sharding vector space.",
                tenant_id,
                project_id,
                count,
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
                    metadata TEXT,
                    category TEXT DEFAULT 'general',
                    quadrant TEXT DEFAULT 'ACTIVE',
                    storage_tier TEXT DEFAULT 'HOT',
                    facet_version INTEGER DEFAULT 2,
                    exergy_score REAL DEFAULT 1.0
                )
            """)  # nosec B608
            emb_def = f"embedding int8[{self._encoder.dimension}]"
            conn.execute(f"CREATE VIRTUAL TABLE {vec_tb} USING vec0({emb_def})")
            conn.execute(
                f"CREATE TABLE {vec_void_tb} (rowid INTEGER PRIMARY KEY, embedding BLOB)"
            )
            # MIH sharded table
            vec_void_mih_tb = f"vec_void_mih_{safe_tenant}_{safe_proj}"
            conn.execute(f"""
                CREATE TABLE {vec_void_mih_tb} (
                    rowid INTEGER PRIMARY KEY,
                    s0 INTEGER, s1 INTEGER, s2 INTEGER, s3 INTEGER,
                    s4 INTEGER, s5 INTEGER, s6 INTEGER, s7 INTEGER,
                    s8 INTEGER, s9 INTEGER, s10 INTEGER, s11 INTEGER,
                    s12 INTEGER, s13 INTEGER, s14 INTEGER, s15 INTEGER
                )
            """)  # nosec B608
            for i in range(16):
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{vec_void_mih_tb}_s{i} "
                    f"ON {vec_void_mih_tb}(s{i})"
                )

            # Migrate only distilled axioms (is_diamond = 1)
            conn.execute(
                f"""
                INSERT INTO {meta_tb} (
                    rowid, id, tenant_id, project_id, content, timestamp,
                    is_diamond, is_bridge, confidence, success_rate,
                    cognitive_layer, parent_decision_id, metadata, exergy_score
                )
                SELECT
                    rowid, id, tenant_id, project_id, content, timestamp,
                    is_diamond, is_bridge, confidence, success_rate,
                    cognitive_layer, parent_decision_id, metadata, exergy_score
                FROM facts_meta
                WHERE tenant_id = ? AND project_id = ? AND is_diamond = 1
            """,
                (tenant_id, project_id),
            )

            conn.execute(
                f"""
                INSERT INTO {vec_tb}(rowid, embedding)
                SELECT v.rowid, v.embedding
                FROM vec_facts v
                JOIN facts_meta m ON v.rowid = m.rowid
                WHERE m.tenant_id = ? AND m.project_id = ? AND m.is_diamond = 1
            """,
                (tenant_id, project_id),
            )

            # Aura-Omega Acceleration: Dedicated indexes for the shard
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{safe_tenant}_{safe_proj}_bridge "
                f"ON {meta_tb}(is_bridge)"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{safe_tenant}_{safe_proj}_layer "
                f"ON {meta_tb}(cognitive_layer)"
            )

            conn.commit()
            return meta_tb, vec_tb, vec_void_tb

        return "facts_meta", "vec_facts", "vec_void"

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
            report = await asyncio.to_thread(
                sanitizer.sanitize, fact.content, tenant_id=fact.tenant_id
            )
            if report.has_pii:
                sanitized_content = report.sanitized
                if report.encrypted_fragments:
                    sanitized_meta["_pii_fragments"] = report.encrypted_fragments
                    sanitized_meta["_pii_categories"] = [c.value for c in report.pii_categories]

        def _offloaded_computations() -> tuple[bytes, bytes, float]:
            ex = calculate_exergy(sanitized_content)
            emb_list = fact.embedding
            if isinstance(emb_list, bytes):
                # Cannot easily dual-quantize from raw bytes without knowing source
                return emb_list, b"", ex

            arr = np.array(emb_list, dtype=np.float32)
            int8_bytes = arr.tobytes()
            binary_bytes = void_vec.pack_void_bit(arr)
            return int8_bytes, binary_bytes, ex

        int8_bytes, binary_bytes, exergy_val = await asyncio.to_thread(_offloaded_computations)

        def _sync_insert() -> None:
            cursor = conn.cursor()
            try:
                meta_tb, vec_tb, vec_void_tb, mih_tb = self._get_domain_tables(
                    conn, fact.tenant_id, fact.project_id
                )
                cursor.execute(
                    f"""
                    INSERT INTO {meta_tb} (
                        id, tenant_id, project_id, content, timestamp,
                        is_diamond, is_bridge, confidence, success_rate,
                        cognitive_layer, parent_decision_id, metadata, exergy_score,
                        category, quadrant, storage_tier, facet_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fact.id,
                        fact.tenant_id,
                        fact.project_id,
                        sanitized_content,
                        fact.timestamp,
                        int(fact.is_diamond),
                        int(fact.is_bridge),
                        fact.confidence,
                        fact.success_rate,
                        fact.cognitive_layer,
                        fact.parent_decision_id,
                        json.dumps(sanitized_meta),
                        exergy_val,
                        fact.category,
                        fact.quadrant,
                        fact.storage_tier,
                        fact.facet_version,
                    ),
                )
                rowid = cursor.lastrowid
                if self._vector_enabled:
                    # Store 1-bit Vector (Legion Recall)
                    if vec_void_tb:
                        cursor.execute(
                            f"INSERT INTO {vec_void_tb}(rowid, embedding) VALUES (?, ?)",
                            (rowid, binary_bytes),
                        )
                        # MIH Indexing
                        from cortex.utils.void_mih import slice_void_bit
                        shards = slice_void_bit(binary_bytes)
                        cursor.execute(
                            f"INSERT INTO {mih_tb} (rowid, s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, "
                            "s10, s11, s12, s13, s14, s15) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (rowid, *shards),
                        )

                    # Store int8 Vector (HdrRecovery Reranking)
                    # Only skip if tier is explicitly COLD to save space
                    if fact.storage_tier != "COLD" and vec_tb:
                        cursor.execute(
                            f"INSERT INTO {vec_tb}(rowid, embedding) "
                            f"VALUES (?, vec_quantize_int8(?, 'unit'))",
                            (rowid, int8_bytes),
                        )
                conn.commit()
            except (sqlite3.Error, RuntimeError) as e:
                conn.rollback()
                logger.error("DB integrity breach during memorize: %s", e)
                raise

        async with self._lock:
            await asyncio.to_thread(_sync_insert)

    async def recall_secure(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
        layer: Optional[str] = None,
    ) -> list[CortexFactModel]:
        """[C5] Recuperación particionada Zero-Trust con ranking SQL nativo."""
        conn = self._get_conn()
        query_vector = await self._encoder.encode(query)

        def _sync_knn_search() -> list[CortexFactModel]:
            rotated_query = encode_query_qjl(query_vector)
            embedding_bytes = np.array(rotated_query, dtype=np.float32).tobytes()
            void_query = void_vec.pack_void_bit(rotated_query)
            now = time.time()

            cursor = conn.cursor()
            meta_tb, vec_tb, vec_void_tb, mih_tb = self._get_domain_tables(
                conn, tenant_id, project_id
            )

            if not self._vector_enabled:
                sql = (
                    f"SELECT * FROM {meta_tb} "
                    "WHERE tenant_id = ? AND (project_id = ? OR is_bridge = 1)"
                )
                params: list[Any] = [tenant_id, project_id]
                if layer:
                    sql += " AND cognitive_layer = ?"
                    params.append(layer)
                sql += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                final_facts = []
                for row in rows:
                    fact = CortexFactModel(
                        id=row["id"],
                        tenant_id=row["tenant_id"],
                        project_id=row["project_id"],
                        content=row["content"],
                        embedding=[],
                        timestamp=row["timestamp"],
                        is_diamond=bool(row["is_diamond"]),
                        is_bridge=bool(row["is_bridge"]),
                        confidence=row["confidence"],
                        cognitive_layer=row["cognitive_layer"],
                        parent_decision_id=row["parent_decision_id"],
                        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    )
                    object.__setattr__(fact, "_recall_score", 0.0)
                    final_facts.append(fact)
                return final_facts

            use_void = False
            if vec_void_tb:
                try:
                    cursor.execute(f"SELECT count(1) FROM {vec_void_tb}")
                    use_void = cursor.fetchone()[0] > 0
                except sqlite3.OperationalError:
                    use_void = False

            if use_void:
                from cortex.utils.void_mih import slice_void_bit
                from cortex.utils.void_vec import void_hamming_dist

                q_shards = slice_void_bit(void_query)

                meta_tb, vec_tb, vec_void_tb, mih_tb = self._get_domain_tables(
                    conn, tenant_id, project_id
                )

                # Candidate criteria: at least 1 shard match (1/16)
                where_mih = " OR ".join([f"s{i} = ?" for i in range(16)])

                # VOID-QUANT v2: Fetch 10x candidates via Hamming and rerank via int8 (HdrRecovery)
                sql_cand = f"""
                    WITH candidates AS (
                        SELECT rowid FROM {mih_tb}
                        WHERE {where_mih}
                        LIMIT ?
                    )
                    SELECT m.*, v.embedding as binary_emb, vf.embedding as int8_emb
                    FROM {meta_tb} m
                    JOIN {vec_void_tb} v ON m.rowid = v.rowid
                    LEFT JOIN {vec_tb} vf ON m.rowid = vf.rowid
                    JOIN candidates c ON m.rowid = c.rowid
                    WHERE m.tenant_id = ? AND (m.project_id = ? OR m.is_bridge = 1)
                """
                # Fetch 10x candidates for reranking
                cursor.execute(sql_cand, (*q_shards, limit * 10, tenant_id, project_id))
                rows = cursor.fetchall()

                if not rows:
                    return []

                final_facts = []
                for row in rows:
                    # ─── HdrRecovery: Use int8 reranking if available ────────
                    if row["int8_emb"]:
                        # Cosine similarity on int8 (Ω₂ precision)
                        cursor.execute(
                            "SELECT 1.0 - vec_distance_cosine(?, "
                            "vec_quantize_int8(?, 'unit')) / 2.0",
                            (row["int8_emb"], embedding_bytes),
                        )
                        sim = cursor.fetchone()[0]
                    else:
                        # Fallback to Hamming similarity
                        dist = void_hamming_dist(void_query, row["binary_emb"])
                        sim = 1.0 - (dist / self._encoder.dimension)

                    if sim < 0.3:
                        continue

                    # Apply Decay, Success, and Exergy Staking
                    decay = cursor.execute(
                        "SELECT cortex_decay(?, ?, ?, ?)",
                        (row["is_diamond"], row["timestamp"], now, self._half_life),
                    ).fetchone()[0]

                    final_score = sim * decay * row["success_rate"] * row["exergy_score"]

                    fact = CortexFactModel(
                        id=row["id"],
                        tenant_id=row["tenant_id"],
                        project_id=row["project_id"],
                        content=row["content"],
                        embedding=row["int8_emb"] or row["binary_emb"],
                        timestamp=row["timestamp"],
                        is_diamond=bool(row["is_diamond"]),
                        is_bridge=bool(row["is_bridge"]),
                        confidence=row["confidence"],
                        cognitive_layer=row["cognitive_layer"],
                        parent_decision_id=row["parent_decision_id"],
                        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    )
                    object.__setattr__(fact, "_recall_score", final_score)
                    final_facts.append(fact)

                # Sort and Limit
                final_facts.sort(key=lambda x: getattr(x, "_recall_score", 0.0), reverse=True)
                return final_facts[:limit]
            else:
                # [KEEP ORIGINAL Non-Void Path for int8 vectors]
                sql = f"""
                    SELECT * FROM (
                        SELECT
                            m.*, v.embedding,
                            (1.0 - vec_distance_cosine(v.embedding,
                                     vec_quantize_int8(?, 'unit')) / 2.0) as base_similarity,
                            ((1.0 - vec_distance_cosine(v.embedding,
                                       vec_quantize_int8(?, 'unit')) / 2.0) *
                             cortex_decay(m.is_diamond, m.timestamp, ?, ?) *
                             m.success_rate * m.exergy_score) as final_score
                        FROM {meta_tb} m
                        JOIN {vec_tb} v ON m.rowid = v.rowid
                        WHERE m.tenant_id = ? AND (m.project_id = ? OR m.is_bridge = 1)
                    ) WHERE base_similarity > 0.3
                    ORDER BY final_score DESC LIMIT ?
                """
                params_vec = [
                    embedding_bytes,
                    embedding_bytes,
                    now,
                    self._half_life,
                    tenant_id,
                    project_id,
                    limit,
                ]
                cursor.execute(sql, tuple(params_vec))
                rows = cursor.fetchall()
                final_facts = []
                for row in rows:
                    fact = CortexFactModel(
                        id=row["id"],
                        tenant_id=row["tenant_id"],
                        project_id=row["project_id"],
                        content=row["content"],
                        embedding=row["embedding"],
                        timestamp=row["timestamp"],
                        is_diamond=bool(row["is_diamond"]),
                        is_bridge=bool(row["is_bridge"]),
                        confidence=row["confidence"],
                        cognitive_layer=row["cognitive_layer"],
                        parent_decision_id=row["parent_decision_id"],
                        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    )
                    object.__setattr__(fact, "_recall_score", row["final_score"])
                    final_facts.append(fact)
                return final_facts

        return await asyncio.to_thread(_sync_knn_search)

    async def recall(
        self, query: str, limit: int = 5, project: Optional[str] = None, tenant_id: str = "default"
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
        """L2 Hybrid Search: Vector KNN + FTS5 BM25 fused via RRF."""
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
        return await self.recall_secure(
            tenant_id=tenant_id, project_id=project_id, query=query, limit=limit
        )

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                self._ready = False
