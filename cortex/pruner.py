"""
CORTEX v5.0 — Embedding Pruner.

Manages embedding lifecycle: archives stale embeddings to cold storage
(hash-only) to prevent unbounded WAL growth under swarm workloads.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

import aiosqlite

__all__ = ['EmbeddingPrunerMixin']

logger = logging.getLogger("cortex.pruner")


def _to_bytes(data: str | bytes | object) -> bytes:
    """Convierte datos de embedding a bytes para hashing."""
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, bytes):
        return data
    return json.dumps(data).encode("utf-8")


class EmbeddingPrunerMixin:
    """Mixin for CortexEngine that provides embedding lifecycle management.

    Strategies:
      - Age-based: Archive embeddings for deprecated facts older than N days.
      - Hash-based: Keep SHA-256 hash of pruned vectors for verification.
    """

    async def prune_stale_embeddings(
        self,
        max_age_days: int = 90,
        dry_run: bool = False,
    ) -> dict:
        """Prune embeddings for facts deprecated more than `max_age_days` ago.

        Moves deprecated fact embeddings to cold storage (pruned_embeddings
        table) keeping only the SHA-256 hash for integrity verification.

        Returns:
            dict with 'pruned_count', 'skipped_count', 'errors'.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        stats = {"pruned_count": 0, "skipped_count": 0, "errors": []}

        async with aiosqlite.connect(self.db_path) as conn:
            # Find deprecated facts with embeddings older than cutoff
            cursor = await conn.execute(
                """
                SELECT ve.fact_id, ve.embedding
                FROM fact_embeddings ve
                JOIN facts f ON f.id = ve.fact_id
                WHERE f.valid_until IS NOT NULL
                  AND f.valid_until < ?
                  AND ve.fact_id NOT IN (
                      SELECT fact_id FROM pruned_embeddings
                  )
                """,
                (cutoff,),
            )
            rows = await cursor.fetchall()

            if dry_run:
                stats["pruned_count"] = len(rows)
                logger.info(
                    "Pruner dry-run: %d embeddings eligible for pruning",
                    len(rows),
                )
                return stats

            for fact_id, embedding_data in rows:
                await self._prune_single_embedding(conn, fact_id, embedding_data, stats)

            await conn.commit()

        logger.info(
            "Pruner complete: %d pruned, %d errors",
            stats["pruned_count"],
            len(stats["errors"]),
        )
        return stats

    async def _prune_single_embedding(self, conn: aiosqlite.Connection, fact_id: int, embedding_data: str | bytes, stats: dict) -> None:
        """Prunes a single embedding and updates stats."""
        try:
            vec_hash = hashlib.sha256(_to_bytes(embedding_data)).hexdigest()
            await conn.execute(
                """
                INSERT OR IGNORE INTO pruned_embeddings
                    (fact_id, hash, dimension, reason)
                VALUES (?, ?, 384, 'deprecated')
                """,
                (fact_id, vec_hash),
            )
            await conn.execute(
                "DELETE FROM fact_embeddings WHERE fact_id = ?",
                (fact_id,),
            )
            stats["pruned_count"] += 1
        except (sqlite3.Error, OSError) as e:
            logger.error("Failed to prune fact_id=%d: %s", fact_id, e)
            stats["errors"].append({"fact_id": fact_id, "error": str(e)})


    async def verify_embedding_hash(self, fact_id: int) -> dict | None:
        """Check if a pruned embedding's hash exists and return metadata.

        Returns:
            dict with 'fact_id', 'hash', 'pruned_at', 'reason' or None.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT fact_id, hash, pruned_at, reason FROM pruned_embeddings WHERE fact_id = ?",
                (fact_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return {
            "fact_id": row[0],
            "hash": row[1],
            "pruned_at": row[2],
            "reason": row[3],
        }

    async def get_pruning_stats(self) -> dict:
        """Get summary statistics about pruned embeddings."""
        async with aiosqlite.connect(self.db_path) as conn:
            active = await conn.execute("SELECT COUNT(*) FROM fact_embeddings")
            active_count = (await active.fetchone())[0]

            try:
                pruned = await conn.execute("SELECT COUNT(*) FROM pruned_embeddings")
                pruned_count = (await pruned.fetchone())[0]
            except (sqlite3.Error, OSError):
                pruned_count = 0

        return {
            "active_embeddings": active_count,
            "pruned_embeddings": pruned_count,
            "total": active_count + pruned_count,
        }
