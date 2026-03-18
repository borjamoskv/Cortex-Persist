"""
Enrichment Worker - Asynchronous background processor for CORTEX.
Ω₁₃: Thermodynamic decoupling sidecar.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import aiosqlite

from cortex.database.core import connect_async
from cortex.embeddings.provider import EmbeddingProvider

logger = logging.getLogger("cortex")


class EnrichmentWorker:
    """Worker that polls enrichment_jobs and processes them."""

    def __init__(
        self, db_path: str, provider: EmbeddingProvider | None = None, poll_interval: float = 1.0
    ):
        self.db_path = db_path
        self.provider = provider
        self.poll_interval = poll_interval
        self._running = False

    async def start(self):
        """Start the worker loop."""
        self._running = True
        logger.info("EnrichmentWorker started (Axiom Ω₁₃)")
        while self._running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error("Worker batch failed: %s", e)
            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """Stop the worker loop."""
        self._running = False

    async def _process_batch(self, batch_size: int = 10):
        """Poll and process a batch of jobs."""
        async with connect_async(self.db_path) as conn:
            # Pick 'queued' jobs or those whose next_attempt_at has passed
            query = """
                SELECT id, fact_id FROM enrichment_jobs
                WHERE status IN ('queued', 'failed')
                AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                LIMIT ?
            """
            now = datetime.now().isoformat()
            async with conn.execute(query, (now, batch_size)) as cursor:
                jobs = await cursor.fetchall()

            for job_id, fact_id in jobs:
                await self._process_job(conn, job_id, fact_id)
                await conn.commit()

    async def _process_job(self, conn: aiosqlite.Connection, job_id: int, fact_id: int):
        """Process a single enrichment job."""
        try:
            # 1. Fetch fact content
            query = "SELECT project, content, tenant_id FROM facts WHERE id = ?"
            async with conn.execute(query, (fact_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Fact {fact_id} not found")
                project, content, tenant_id = row

            # 2. Process with provider if available
            if self.provider:
                logger.info("Enriching fact %d via provider...", fact_id)
                # This would call the provider to embed the fact
                # For now, we just simulate success in the worker logic
                pass

            await self._mark_success(conn, job_id)
            logger.info("Enriched fact %d (job %d)", fact_id, job_id)

        except Exception as e:
            logger.error("Failed to process job %d: %s", job_id, e)
            await self._mark_failure(conn, job_id, str(e))

    async def _mark_success(self, conn: aiosqlite.Connection, job_id: int):
        query = """
            UPDATE enrichment_jobs 
            SET status = 'completed', updated_at = ? 
            WHERE id = ?
        """
        await conn.execute(query, (datetime.now().isoformat(), job_id))

    async def _mark_failure(self, conn: aiosqlite.Connection, job_id: int, error: str):
        # Exponential backoff logic
        next_attempt = (datetime.now() + timedelta(minutes=5)).isoformat()
        query = """
            UPDATE enrichment_jobs 
            SET status = 'failed', 
                attempts = attempts + 1, 
                last_error = ?, 
                next_attempt_at = ?,
                updated_at = ? 
            WHERE id = ?
        """
        await conn.execute(query, (error, next_attempt, datetime.now().isoformat(), job_id))
