import asyncio
import json
import logging
import time
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from cortex import config
from cortex.database.pool import CortexConnectionPool
from cortex.embeddings.manager import EmbeddingManager

logger = logging.getLogger("cortex.specialists.memento.ledger")

class MementoStage(str, Enum):
    BUFFERING = "BUFFERING"
    ANALYZING = "ANALYZING"
    CRYSTALLIZED = "CRYSTALLIZED"
    PERSISTED = "PERSISTED"
    REJECTED = "REJECTED"
    GC = "GC"

class MementoLedger:
    """CORTEX Ledger integration for Memento Specialist.

    Optimized for cognitive archaeology via sqlite-vec and async pooling.
    """

    TABLE_NAME = "memento_memory_transition"
    
    def __init__(self, engine: Any | None = None, db_path: Optional[str] = None) -> None:
        self._engine = engine
        self._db_path = db_path or config.DB_PATH
        self._pool = CortexConnectionPool(self._db_path, read_only=False)
        self._embedder = EmbeddingManager(engine) if engine is not None else EmbeddingManager(None)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the vectorized ledger table."""
        if self._initialized:
            return
            
        async with self._pool.acquire() as conn:
            # Create standard table with integer oid for vector mapping
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    oid INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE,
                    session_id TEXT,
                    trace_id TEXT,
                    stage TEXT,
                    summary TEXT,
                    evidence TEXT,
                    exergy_delta REAL,
                    hours_saved REAL,
                    metadata TEXT,
                    timestamp REAL
                )
            """)
            
            # Create virtual vector table for semantic search
            dim = 768
            if self._embedder:
                dim = self._embedder.dimension

            # Check if table exists and has correct dimension
            recreate_index = False
            async with conn.execute(f"SELECT sql FROM sqlite_master WHERE name='{self.TABLE_NAME}_idx'") as cursor:
                row = await cursor.fetchone()
                if row:
                    existing_sql = row[0]
                    if f"float[{dim}]" not in existing_sql:
                        recreate_index = True
                        logger.warning(
                            "[MementoLedger] Dimension mismatch in %s_idx. Dropping and re-creating.",
                            self.TABLE_NAME
                        )

            if recreate_index:
                await conn.execute(f"DROP TABLE {self.TABLE_NAME}_idx")

            await conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS {self.TABLE_NAME}_idx "
                f"USING vec0(embedding float[{dim}])"
            )

            await conn.commit()
            
        async with self._pool.acquire() as conn:
            # Handle migration: Rename entropy_delta to exergy_delta
            async with conn.execute(f"PRAGMA table_info({self.TABLE_NAME})") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
                if 'exergy_delta' not in columns:
                    if 'entropy_delta' in columns:
                        await conn.execute(f"ALTER TABLE {self.TABLE_NAME} RENAME COLUMN entropy_delta TO exergy_delta")
                        logger.info("[MementoLedger] Migrated entropy_delta → exergy_delta (Ω₂)")
                    else:
                        await conn.execute(f"ALTER TABLE {self.TABLE_NAME} ADD COLUMN exergy_delta REAL DEFAULT 0.0")
                
                if 'session_id' not in columns:
                    await conn.execute(f"ALTER TABLE {self.TABLE_NAME} ADD COLUMN session_id TEXT")
                    logger.info("[MementoLedger] Added session_id column for isolation (Ω₄)")

            await conn.commit()

        self._initialized = True
        logger.info("[MementoLedger] Vectorized ledger initialized at %s", self._db_path)

    def _make_fact(
        self,
        session_id: str,
        trace_id: str,
        stage: MementoStage,
        summary: str,
        exergy_delta: float = 0.0,
        hours_saved: float = 0.0,
        evidence: str = "",
        extra: dict | None = None,
    ) -> dict:
        return {
            "id": str(uuid4()),
            "session_id": session_id,
            "trace_id": trace_id,
            "stage": stage.value,
            "summary": summary,
            "evidence": evidence,
            "exergy_delta": float(f"{exergy_delta:.4f}"),
            "hours_saved": float(f"{hours_saved:.2f}"),
            "metadata": json.dumps(extra or {}),
            "timestamp": time.time(),
        }

    async def record_transition(
        self,
        session_id: str,
        trace_id: str,
        stage: MementoStage,
        summary: str,
        exergy_delta: float = 0.0,
        hours_saved: float = 0.0,
        evidence: str = "",
        extra: dict | None = None,
    ) -> None:
        """Record a lifecycle state change with optional vector embedding."""
        if not self._initialized:
            await self.initialize()

        fact = self._make_fact(session_id, trace_id, stage, summary, exergy_delta, hours_saved, evidence, extra)
        
        async with self._pool.acquire() as conn:
            # 1. Insert structured data
            cursor = await conn.execute(f"""
                INSERT INTO {self.TABLE_NAME} 
                (id, session_id, trace_id, stage, summary, evidence, exergy_delta, hours_saved, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fact["id"], fact["session_id"], fact["trace_id"], fact["stage"], 
                fact["summary"], fact["evidence"], fact["exergy_delta"], 
                fact["hours_saved"], fact["metadata"], fact["timestamp"]
            ))
            oid = cursor.lastrowid
            
            # 2. Insert vector embedding if possible
            if self._embedder:
                try:
                    # Embed combined summary + evidence for semantic context
                    text_to_embed = f"{summary} {evidence}"
                    # Wrap blocking NN inference in to_thread (Ω₇)
                    embedding = await asyncio.to_thread(self._embedder.embed, text_to_embed)
                    if embedding and isinstance(embedding, list):
                        if isinstance(embedding[0], list):  # Batch result
                            embedding = embedding[0]

                        import struct
                        embedding_blob = struct.pack(f"{len(embedding)}f", *embedding)

                        await conn.execute(
                            f"INSERT INTO {self.TABLE_NAME}_idx (rowid, embedding) "
                            f"VALUES (?, ?)",
                            (oid, embedding_blob)
                        )
                except Exception as e:
                    logger.warning("[MementoLedger] Vector embedding failed: %s", e)

            await conn.commit()
            
        logger.info("[MementoLedger] %s -> %s | Exergy Δ=%.3f", summary, stage.value, exergy_delta)

    async def semantic_search(self, query: str, session_id: Optional[str] = None, limit: int = 5) -> list[dict]:
        """Search cognitive transitions by semantic context."""
        if not self._initialized or not self._embedder:
            logger.warning("[MementoLedger] Search called before initialization or without embedder.")
            return []
            
        # Wrap blocking NN inference in to_thread (Ω₇)
        embedding = await asyncio.to_thread(self._embedder.embed, query)
        if not (isinstance(embedding, list) and len(embedding) > 0):
            return []
            
        if isinstance(embedding[0], list):
            embedding = embedding[0]

        import struct
        embedding_blob = struct.pack(f"{len(embedding)}f", *embedding)

        async with self._pool.acquire() as conn:
            where_clause = "WHERE v.embedding MATCH ? AND k = ?"
            params: list[Any] = [embedding_blob, int(limit)]
            
            if session_id:
                where_clause += " AND t.session_id = ?"
                params.append(session_id)

            cursor = await conn.execute(f"""
                SELECT t.*, v.distance
                FROM {self.TABLE_NAME} t
                JOIN {self.TABLE_NAME}_idx v ON t.oid = v.rowid
                {where_clause}
                ORDER BY distance
                LIMIT ?
            """, (*params, int(limit)))
            
            rows = await cursor.fetchall()
            if not rows:
                return []
                
            desc = cursor.description
            if not desc:
                return []
                
            return [dict(zip([col[0] for col in desc], row, strict=True)) for row in rows]
        
        return []

    async def get_stats(self, session_id: Optional[str] = None) -> dict:
        """Return memory lifecycle statistics from DB."""
        if not self._initialized:
            await self.initialize()
            
        where_clause = ""
        params: list[Any] = []
        if session_id:
            where_clause = "WHERE session_id = ?"
            params.append(session_id)

        async with self._pool.acquire() as conn:
            count = 0
            total_hours = 0.0
            async with conn.execute(f"SELECT COUNT(*), SUM(hours_saved) FROM {self.TABLE_NAME} {where_clause}", params) as cur:
                row = await cur.fetchone()
                if row:
                    count = row[0] or 0
                    total_hours = row[1] or 0.0
            
            stages = {}
            async with conn.execute(f"SELECT stage, COUNT(*) FROM {self.TABLE_NAME} {where_clause} GROUP BY stage", params) as cur:
                async for stage_row in cur:
                    stages[stage_row[0]] = stage_row[1]
                
        return {
            "total_facts": count,
            "total_hours_saved": float(f"{total_hours:.2f}"),
            "stages": stages
        }

    async def prune_low_exergy(
        self, session_id: str | None = None, threshold: float = 0.05,
    ) -> int:
        """Remove traces below the exergy threshold. Returns rows deleted."""
        if not self._initialized:
            await self.initialize()

        params: list[Any] = [threshold]
        where = "WHERE exergy_delta < ? AND stage != ?"
        params.append(MementoStage.PERSISTED.value)

        if session_id:
            where += " AND session_id = ?"
            params.append(session_id)

        async with self._pool.acquire() as conn:
            # Delete matching vector rows first (referential cleanup)
            cursor = await conn.execute(
                f"SELECT oid FROM {self.TABLE_NAME} {where}", params,
            )
            oids = [row[0] for row in await cursor.fetchall()]

            if oids:
                placeholders = ",".join("?" * len(oids))
                await conn.execute(
                    f"DELETE FROM {self.TABLE_NAME}_idx "
                    f"WHERE rowid IN ({placeholders})",
                    oids,
                )
                await conn.execute(
                    f"DELETE FROM {self.TABLE_NAME} "
                    f"WHERE oid IN ({placeholders})",
                    oids,
                )
                await conn.commit()

            logger.info(
                "[MementoLedger] Pruned %d low-exergy traces (threshold=%.3f)",
                len(oids), threshold,
            )
            return len(oids)

    async def merge_duplicates(self, session_id: str | None = None) -> int:
        """Deduplicate entries with identical summary+stage, keeping latest."""
        if not self._initialized:
            await self.initialize()

        where = ""
        params: list[Any] = []
        if session_id:
            where = "AND session_id = ?"
            params.append(session_id)

        async with self._pool.acquire() as conn:
            # Find duplicate groups, keep max(oid)
            cursor = await conn.execute(f"""
                SELECT GROUP_CONCAT(oid) AS oids
                FROM {self.TABLE_NAME}
                WHERE 1=1 {where}
                GROUP BY summary, stage, session_id
                HAVING COUNT(*) > 1
            """, params)

            total_removed = 0
            for row in await cursor.fetchall():
                oid_list = [int(x) for x in row[0].split(",")]
                keep = max(oid_list)
                remove = [o for o in oid_list if o != keep]
                if remove:
                    ph = ",".join("?" * len(remove))
                    await conn.execute(
                        f"DELETE FROM {self.TABLE_NAME}_idx "
                        f"WHERE rowid IN ({ph})", remove,
                    )
                    await conn.execute(
                        f"DELETE FROM {self.TABLE_NAME} "
                        f"WHERE oid IN ({ph})", remove,
                    )
                    total_removed += len(remove)

            await conn.commit()
            logger.info(
                "[MementoLedger] Merged %d duplicate traces", total_removed,
            )
            return total_removed

    async def shutdown(self) -> None:
        """Close the connection pool."""
        if hasattr(self, "_pool"):
            await self._pool.close()
            logger.info("[MementoLedger] Connection pool closed.")
