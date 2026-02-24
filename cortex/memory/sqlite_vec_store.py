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

logger = logging.getLogger("cortex.memory.sqlite_vec_store")


def cortex_decay(is_diamond: int, timestamp: float, current_time: float, half_life: float) -> float:
    """Calcula el decaimiento temporal soberano."""
    if is_diamond:
        return 1.0
    age = max(0.0, current_time - timestamp)
    return float((0.5) ** (age / half_life))


class SovereignVectorStoreL2:
    """Async vector store for CORTEX v6 L2 semantic memory.

    Uses `sqlite-vec` for extremely fast, local, zero-trust vector recall.
    Calculates final scores based on Cosine Similarity, Temporal Decay,
    and OUROBOROS success_rate.
    """

    __slots__ = ("_db_path", "_encoder", "_conn", "_lock", "_ready", "_half_life")

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

            self._conn.commit()
            self._ready = True
        return self._conn

    async def memorize(self, fact: CortexFactModel) -> None:
        """Encode and store a multi-tenant CortexFactModel."""
        conn = self._get_conn()

        async with self._lock:
            embedding_bytes = np.array(fact.embedding, dtype=np.float32).tobytes()

            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO facts_meta (
                    id, tenant_id, project_id, content, timestamp,
                    is_diamond, is_bridge, confidence, success_rate, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
            rowid = cursor.lastrowid

            cursor.execute(
                "INSERT INTO vec_facts(rowid, embedding) VALUES (?, ?)", (rowid, embedding_bytes)
            )
            conn.commit()

    async def recall_secure(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
    ) -> list[CortexFactModel]:
        """[C5] Recuperación particionada Zero-Trust con ranking SQL nativo."""
        conn = self._get_conn()
        query_vector = await self._encoder.encode(query)
        embedding_bytes = np.array(query_vector, dtype=np.float32).tobytes()
        now = time.time()

        # Vector search + Reranking in SQL
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                m.id, m.tenant_id, m.project_id, m.content, m.timestamp,
                m.is_diamond, m.is_bridge, m.confidence, m.success_rate, m.metadata,
                ((1.0 - vec_distance_cosine(v.embedding, ?) / 2.0) *
                 cortex_decay(m.is_diamond, m.timestamp, ?, ?) *
                 m.success_rate) as final_score
            FROM facts_meta m
            JOIN vec_facts v ON m.rowid = v.rowid
            WHERE m.tenant_id = ? AND (m.project_id = ? OR m.is_bridge = 1)
            ORDER BY final_score DESC
            LIMIT ?
            """,
            (embedding_bytes, now, self._half_life, tenant_id, project_id, limit),
        )

        rows = cursor.fetchall()
        final_facts = []

        for row in rows:
            score = row["final_score"]

            # Fetch embedding
            v_cursor = conn.cursor()
            v_cursor.execute(
                "SELECT embedding FROM vec_facts WHERE rowid = "
                "(SELECT rowid FROM facts_meta WHERE id = ?)",
                (row["id"],),
            )
            v_row = v_cursor.fetchone()
            emb = np.frombuffer(v_row["embedding"], dtype=np.float32).tolist() if v_row else []

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
                success_rate=row["success_rate"],
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

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                self._ready = False
