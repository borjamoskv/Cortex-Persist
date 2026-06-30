# [C5-REAL] Exergy-Maximized
"""
Re-indexing Pipeline for Vector Embeddings (Ω₁).

Handles migration and re-embedding when the EmbeddingProvider or dimension changes
(e.g., from Local [384] to API [768] or due to an algorithmic update).
"""

import asyncio
import logging
from typing import Any

from babylon60.embeddings.manager import EmbeddingManager

logger = logging.getLogger("babylon60.embeddings.reindex")


class ReindexPipeline:
    """Manages full vector re-indexing for semantic search."""

    def __init__(self, engine: Any, manager: EmbeddingManager):
        self.engine = engine
        self.manager = manager

    async def get_current_db_dimension(self) -> int | None:
        """Check the currently configured dimension of the fact_embeddings table."""
        async with self.engine.session() as conn:
            try:
                # In sqlite-vec, we can query sqlite_master for the table creation SQL
                cursor = await conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='fact_embeddings'"
                )
                row = await cursor.fetchone()
                if not row or not row[0]:
                    return None

                sql = row[0].upper()
                # Parse FLOAT[N]
                if "FLOAT[" in sql:
                    start = sql.find("FLOAT[") + 6
                    end = sql.find("]", start)
                    return int(sql[start:end])
                return None
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not determine current db dimension: %s", e)
                return None

    async def execute_reindex(
        self, tenant_id: str = "default", batch_size: int = 100
    ) -> dict[str, Any]:
        """Drop current embeddings, recreate with new dimension, and re-embed all facts."""
        target_dim = self.manager.dimension
        current_dim = await self.get_current_db_dimension()

        logger.info(
            "Starting Re-indexing Pipeline. Target dimension: %d, Current DB dimension: %s",
            target_dim,
            current_dim,
        )

        async with self.engine.session() as conn:
            # 1. Drop old tables
            await conn.execute("DROP TABLE IF EXISTS fact_embeddings")
            # 2. Recreate tables with correct dimension
            await conn.execute(f"""
                CREATE VIRTUAL TABLE fact_embeddings USING vec0(
                    fact_id INTEGER PRIMARY KEY,
                    embedding FLOAT[{target_dim}]
                )
            """)

            # 3. Fetch all facts for the tenant
            cursor = await conn.execute(
                "SELECT id, content, project FROM facts WHERE tenant_id = ? AND valid_until IS NULL",
                (tenant_id,),
            )
            rows = await cursor.fetchall()

            total = len(rows)
            success = 0
            failed = 0

            # 4. Batch re-embed
            from babylon60.engine.core.embedding_engine import embed_fact_async

            embedder = self.manager._get_embedder()
            mem_mgr = getattr(self.engine, "_memory_manager", None)

            # Process in batches to avoid OOM
            for i in range(0, total, batch_size):
                batch = rows[i : i + batch_size]
                tasks = []
                for row in batch:
                    fact_id, content, project = row
                    # Bypass event loop blocking by scheduling them concurrently
                    tasks.append(
                        embed_fact_async(
                            conn=conn,
                            fact_id=fact_id,
                            project=project,
                            content=content,
                            embedder=embedder,
                            memory_manager=mem_mgr,
                            tenant_id=tenant_id,
                        )
                    )

                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        failed += 1
                        logger.error("Failed to re-embed fact: %s", res)
                    else:
                        success += 1

                # Commit intermediate progress
                await conn.commit()
                logger.info(
                    "Re-indexing progress: %d/%d facts processed", min(i + batch_size, total), total
                )

            # Record re-index event in the ledger
            try:
                import time

                from babylon60.crypto.hash_registry import cortex_hash

                payload = f"reindex:{tenant_id}:{target_dim}:{total}:{int(time.time())}"
                await conn.execute(
                    "INSERT INTO transactions (tenant_id, project, action, detail, hash) VALUES (?, ?, ?, ?, ?)",
                    (
                        tenant_id,
                        "system",
                        "REINDEX_EMBEDDINGS",
                        f"Re-indexed {success} facts to dim {target_dim}",
                        cortex_hash(payload.encode()),
                    ),
                )
                await conn.commit()
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to emit ledger event for re-indexing: %s", e)

        return {"total_facts": total, "success": success, "failed": failed, "dimension": target_dim}
