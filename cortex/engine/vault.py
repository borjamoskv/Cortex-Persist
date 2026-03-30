import asyncio
import logging
import sqlite3
from typing import Any, Optional

import aiosqlite


logger = logging.getLogger("cortex.vault")

_sentence_model: Any = None
_model_lock = asyncio.Lock()


async def _get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        async with _model_lock:
            # Re-check after acquiring lock
            if _sentence_model is None:
                logger.info("VAULT: Lazy loading sentence-transformers (all-MiniLM-L6-v2)")
                from sentence_transformers import SentenceTransformer
                # Use to_thread if SentenceTransformer load is slow
                _sentence_model = await asyncio.to_thread(SentenceTransformer, "all-MiniLM-L6-v2")
    return _sentence_model


def _get_sqlite_vec_path():
    import sqlite_vec
    return sqlite_vec.loadable_path()


class ConceptVault:
    """⚖️ ConceptVault: Persistent memory for Legion OMEGA (v6.3 Vectorial)."""

    def __init__(self, db_path: str = "cortex_legion.db"):
        self.db_path = db_path

    async def _setup_conn(self, conn: aiosqlite.Connection):
        """Load extensions for an existing connection."""
        try:
            await conn.enable_load_extension(True)
            await conn.load_extension(_get_sqlite_vec_path())
        except Exception as e:
            logger.error("VAULT: Failed to load sqlite-vec: %s", e)

    async def init(self):
        """Initialize SQLite schema for vector concepts."""
        async with aiosqlite.connect(self.db_path) as conn:
            await self._setup_conn(conn)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS legion_concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent TEXT NOT NULL,
                    code_snippet TEXT NOT NULL,
                    exergy REAL NOT NULL,
                    usage_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_intent ON legion_concepts(intent)")

            try:
                await conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vec_concepts USING vec0(
                        embedding float[384]
                    )
                """)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    logger.error("VAULT: Virtual table creation error: %s", e)
            await conn.commit()

    async def crystallize(self, intent: str, code: str, exergy: float):
        """Crystallize a successful forge into the vault using vector embeddings."""
        logger.info("VAULT: Crystallizing concept for '%s' (Exergy: %.2f)", intent, exergy)
        model = await _get_sentence_model()
        # Ensure we have the model object, not a coroutine
        emb = model.encode([intent])[0].tobytes()

        async with aiosqlite.connect(self.db_path) as conn:
            await self._setup_conn(conn)
            cursor = await conn.execute("""
                INSERT INTO legion_concepts (intent, code_snippet, exergy)
                VALUES (?, ?, ?)
            """, (intent, code, exergy))
            rowid = cursor.lastrowid

            await conn.execute("""
                INSERT INTO vec_concepts(rowid, embedding)
                VALUES (?, ?)
            """, (rowid, emb))
            await conn.commit()

    async def find_warm_start(self, intent: str) -> Optional[str]:
        """Find a similar concept for a 'warm start' prompt injection using K-NN vector search."""
        model = await _get_sentence_model()
        emb = model.encode([intent])[0].tobytes()

        async with aiosqlite.connect(self.db_path) as conn:
            await self._setup_conn(conn)
            try:
                cursor = await conn.execute("""
                    SELECT lc.code_snippet, sub.distance
                    FROM (
                        SELECT rowid, distance
                        FROM vec_concepts
                        WHERE embedding MATCH ?
                        ORDER BY distance
                        LIMIT 1
                    ) sub
                    JOIN legion_concepts lc ON lc.id = sub.rowid
                """, (emb,))
                row = await cursor.fetchone()
                if row:
                    code_snippet, distance = row
                    if distance < 1.0:
                        logger.debug("VAULT: Warm start found for '%s' (Distance: %.3f)",
                                     intent, distance)
                        return code_snippet
            except sqlite3.OperationalError as e:
                logger.error("VAULT: Vector search failed: %s", e)
        return None

    async def get_all_concepts(self) -> list[dict[str, Any]]:
        """Retrieve all crystallized concepts."""
        async with aiosqlite.connect(self.db_path) as conn:
            # Note: no need to load extensions for simple SELECT
            cursor = await conn.execute("SELECT intent, exergy, usage_count FROM legion_concepts")
            rows = await cursor.fetchall()
            return [{"intent": r[0], "exergy": r[1], "usage_count": r[2]} for r in rows]
