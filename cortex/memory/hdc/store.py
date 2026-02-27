"""CORTEX v7 — Sovereign HDC Vector Store.

Replaces dense Qdrant/sqlite-vec storage with purely NumPy/SQLite HDC vectors.
Supports normal semantic recall AND 'traceable unbinding' to extract the
reasons why a fact matched a query.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

import numpy as np

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

from cortex.memory.hdc.algebra import unbind
from cortex.memory.hdc.codec import HDCEncoder
from cortex.memory.hdc.item_memory import ItemMemory
from cortex.memory.models import CortexFactModel
from cortex.memory.sqlite_vec_store import cortex_decay

__all__ = ["HDCVectorStoreL2"]

logger = logging.getLogger("cortex.memory.hdc.store")


class HDCVectorStoreL2:
    """Async vector store for CORTEX v7 L2 semantic memory (Hyperdimensional).

    Uses sqlite-vec (with int8 embeddings mapped to float32 for compatibility,
    or pure numpy if sqlite-vec doesn't support int8 cosine directly yet).
    Since sqlite-vec expects float32, we cast int8 to float32 upon insert.
    The storage penalty is accepted for phase 1 of Vector Alpha to reuse sqlite-vec ranking.
    """

    __slots__ = (
        "_db_path",
        "_encoder",
        "_item_memory",
        "_conn",
        "_lock",
        "_ready",
        "_half_life",
    )

    def __init__(
        self,
        encoder: HDCEncoder,
        item_memory: ItemMemory,
        db_path: str | Path = "~/.cortex/hdc_vectors.db",
        half_life_days: int = 7,
    ) -> None:
        self._encoder = encoder
        self._item_memory = item_memory
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()
        self._ready = False
        self._half_life = half_life_days * 24 * 3600

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if sqlite_vec is None:
                err = "sqlite_vec module not installed. Run 'pip install sqlite-vec'"
                raise RuntimeError(err)

            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.row_factory = sqlite3.Row

            # Register Sovereign Functions
            self._conn.create_function("cortex_decay", 4, cortex_decay)

            # Facts Meta Table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS hdc_facts_meta (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    content TEXT,
                    timestamp REAL,
                    is_diamond INTEGER,
                    is_bridge INTEGER,
                    confidence TEXT,
                    success_rate REAL,
                    metadata TEXT,
                    fact_type TEXT
                )
            """)

            # Vector Table (sqlite-vec uses float[N])
            dim = self._encoder.dimension
            self._conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS hdc_vec_facts USING vec0(
                    embedding float[{dim}]
                )
            """)

            # Specular Vector Table (G10 Intent Alignment)
            self._conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS hdc_specular_vec_facts USING vec0(
                    embedding float[{dim}]
                )
            """)

            # Indexes
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tenant_proj ON "
                "hdc_facts_meta(tenant_id, project_id)"
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_bridge ON hdc_facts_meta(is_bridge)")

            self._conn.commit()
            self._ready = True
        return self._conn

    async def memorize(self, fact: CortexFactModel, fact_type: str | None = None) -> None:
        """Encode and store a multi-tenant CortexFactModel as a Hypervector."""
        conn = self._get_conn()

        async with self._lock:
            # 1. Algebraic Encoding
            # Pass fact_type and project_id to bind them into the composite memory
            f_type = fact_type or fact.metadata.get("type", "general")
            hv = self._encoder.encode_fact(
                content=fact.content,
                fact_type=f_type,
                project_id=fact.project_id,
            )

            # 2. Store: cast int8 to float32 for sqlite-vec compatibility
            embedding_bytes = np.array(hv, dtype=np.float32).tobytes()

            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO hdc_facts_meta (
                    id, tenant_id, project_id, content, timestamp,
                    is_diamond, is_bridge, confidence, success_rate, metadata, fact_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.id,
                    fact.tenant_id,
                    fact.project_id,
                    fact.content,
                    fact.timestamp,
                    int(fact.is_diamond),
                    int(fact.is_bridge),
                    fact.confidence,
                    fact.success_rate,
                    json.dumps(fact.metadata),
                    f_type,
                ),
            )
            rowid = cursor.lastrowid

            cursor.execute(
                "INSERT INTO hdc_vec_facts(rowid, embedding) VALUES (?, ?)",
                (rowid, embedding_bytes),
            )

            # 3. Store Specular Trace if available
            if getattr(fact, "specular_embedding", None):
                spec_bytes = np.array(fact.specular_embedding, dtype=np.float32).tobytes()
                cursor.execute(
                    "INSERT INTO hdc_specular_vec_facts(rowid, embedding) VALUES (?, ?)",
                    (rowid, spec_bytes),
                )

            conn.commit()

            # Save codebook after potential new tokens are added
            self._item_memory.save_codebook()

    async def recall_secure(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
        fact_type: str | None = None,
        inhibit_ids: list[str] | None = None,
    ) -> list[CortexFactModel]:
        """Recuperación particionada Zero-Trust con Inhibición de Vectores Tóxicos.

        Args:
            tenant_id: Boundary isolation.
            project_id: Project scope.
            query: Search string.
            limit: Max results.
            fact_type: Optional role filtering.
            inhibit_ids: Optional list of fact IDs whose vectors should suppress results.
        """
        conn = self._get_conn()

        # Query encoding
        query_hv = self._encoder.encode_fact(
            content=query, fact_type=fact_type, project_id=project_id
        )
        embedding_bytes = np.array(query_hv, dtype=np.float32).tobytes()
        now = time.time()

        # Retrieve toxic vectors if inhibit_ids are provided
        toxic_hvs = self._fetch_toxic_hvs(conn, inhibit_ids)

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                m.rowid, m.id, m.tenant_id, m.project_id, m.content, m.timestamp,
                m.is_diamond, m.is_bridge, m.confidence, m.success_rate, m.metadata, m.fact_type,
                ((1.0 - vec_distance_cosine(v.embedding, ?) / 2.0) *
                 cortex_decay(m.is_diamond, m.timestamp, ?, ?) *
                 m.success_rate) as final_score
            FROM hdc_facts_meta m
            JOIN hdc_vec_facts v ON m.rowid = v.rowid
            WHERE m.tenant_id = ? AND (m.project_id = ? OR m.is_bridge = 1)
            ORDER BY final_score DESC
            LIMIT ?
            """,
            (embedding_bytes, now, self._half_life, tenant_id, project_id, limit * 2),
        )

        rows = cursor.fetchall()
        final_facts = []

        for row in rows:
            fact = self._process_hdc_fact_row(conn, row, toxic_hvs)
            final_facts.append(fact)

        # Re-sort and limit after inhibition
        final_facts.sort(key=lambda x: getattr(x, "_recall_score", 0.0), reverse=True)
        return final_facts[:limit]

    def _fetch_toxic_hvs(
        self, conn: sqlite3.Connection, inhibit_ids: list[str] | None
    ) -> list[np.ndarray]:
        """Fetch toxic vectors for inhibition."""
        toxic_hvs = []
        if inhibit_ids:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(inhibit_ids))
            cursor.execute(
                f"SELECT embedding FROM hdc_vec_facts WHERE rowid IN "
                f"(SELECT rowid FROM hdc_facts_meta WHERE id IN ({placeholders}))",
                inhibit_ids,
            )
            for v_row in cursor.fetchall():
                toxic_hvs.append(np.frombuffer(v_row["embedding"], dtype=np.float32))
        return toxic_hvs

    def _process_hdc_fact_row(
        self, conn: sqlite3.Connection, row: sqlite3.Row, toxic_hvs: list[np.ndarray]
    ) -> CortexFactModel:
        """Process a single row from the HDC recall query."""
        score = row["final_score"]
        emb_f32 = None

        # Fetch embedding for inhibition check and models
        v_cursor = conn.cursor()
        v_cursor.execute("SELECT embedding FROM hdc_vec_facts WHERE rowid = ?", (row["rowid"],))
        v_row = v_cursor.fetchone()
        if v_row:
            emb_f32 = np.frombuffer(v_row["embedding"], dtype=np.float32)

        # APPLY INHIBITION (Vector Gamma)
        if toxic_hvs and emb_f32 is not None:
            for thv in toxic_hvs:
                interference = np.dot(emb_f32, thv) / self._encoder.dimension
                if interference > 0.05:
                    score *= 1.0 - (interference * 2.0)
                    score = max(0.01, score)
                    logger.info(
                        "☢️ Vector Gamma: Inhibition applied to %s (interference: %.2f)",
                        row["id"],
                        interference,
                    )

        # Revert float32 back to int8
        emb_int8 = []
        if emb_f32 is not None:
            emb_int8_arr = np.sign(emb_f32).astype(np.int8)
            emb_int8_arr[emb_int8_arr == 0] = 1
            emb_int8 = emb_int8_arr.tolist()

        # Retrieve specular embedding
        specular_emb = None
        s_cursor = conn.cursor()
        s_cursor.execute(
            "SELECT embedding FROM hdc_specular_vec_facts WHERE rowid = ?", (row["rowid"],)
        )
        s_row = s_cursor.fetchone()
        if s_row:
            s_emb_f32 = np.frombuffer(s_row["embedding"], dtype=np.float32)
            s_emb_int8 = np.sign(s_emb_f32).astype(np.int8)
            s_emb_int8[s_emb_int8 == 0] = 1
            specular_emb = s_emb_int8.tolist()

        fact = CortexFactModel(
            id=row["id"],
            tenant_id=row["tenant_id"],
            project_id=row["project_id"],
            content=row["content"],
            embedding=emb_int8,
            timestamp=row["timestamp"],
            is_diamond=bool(row["is_diamond"]),
            is_bridge=bool(row["is_bridge"]),
            confidence=row["confidence"],
            success_rate=row["success_rate"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            specular_embedding=specular_emb,
        )

        object.__setattr__(fact, "_recall_score", score)
        object.__setattr__(fact, "_fact_type", row["fact_type"])
        return fact

    async def recall(
        self,
        query: str,
        limit: int = 5,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list[CortexFactModel]:
        """Backward-compatible recall."""
        return await self.recall_secure(
            tenant_id=tenant_id, project_id=project or "default", query=query, limit=limit
        )

    async def get_toxic_ids(self, tenant_id: str, project_id: str, limit: int = 10) -> list[str]:
        """Retrieve IDs of toxic facts (error violations) for inhibition."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM hdc_facts_meta
            WHERE tenant_id = ? AND (project_id = ? OR is_bridge = 1)
            AND fact_type = 'error' AND metadata LIKE '%"is_toxic": true%'
            ORDER BY timestamp DESC LIMIT ?
            """,
            (tenant_id, project_id, limit),
        )
        ids = [row["id"] for row in cursor.fetchall()]
        # print(f"DEBUG: Found {len(ids)} toxic IDs for {tenant_id}/{project_id}")
        return ids

    def extract_traces(self, fact: CortexFactModel) -> dict[str, Any]:
        """ULTRATHINK-DEEP Traceability feature.

        Unbinds the fact hypervector to determine its components
        (project, role, and strongest tokens) without needing the DB metadata.
        """
        if not fact.embedding:
            return {}

        hv = np.array(fact.embedding, dtype=np.int8)
        traces = {}

        # 1. Unbind project and role if available via ItemMemory
        metadata_type = getattr(fact, "_fact_type", "general")
        role_hv = self._item_memory.role_vector(metadata_type)
        proj_hv = self._item_memory.project_vector(fact.project_id)

        # Try to unbind project and see what remains
        # Unbinding project leaves (content ⊗ role)
        sans_proj = unbind(hv, proj_hv)

        # Unbind role implies we get the pure content bundle
        content_bundle = unbind(sans_proj, role_hv)

        # 2. Extract top matching tokens from the codebook
        # We search the item memory for tokens that correlate highly with the content_bundle.
        # Note: In bundling (majority vote), the constituent vectors retain some correlation
        # with the bundle, but permuted positional vectors won't match direct token queries.
        # This acts as a crude "bag of words" trace.
        nearest_symbols = self._item_memory.nearest(content_bundle, top_k=5)
        traces["top_symbols"] = nearest_symbols

        return traces

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                self._ready = False
