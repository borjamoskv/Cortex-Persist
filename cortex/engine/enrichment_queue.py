"""
Enrichment Queue management for P0 Decoupling.
"""

from __future__ import annotations

import logging

import aiosqlite

logger = logging.getLogger("cortex")


async def enqueue_enrichment_job(
    conn: aiosqlite.Connection, fact_id: int, commit: bool = False
) -> int:
    """Add a new fact to the enrichment queue."""
    query = "INSERT INTO enrichment_jobs (fact_id) VALUES (?)"
    async with conn.execute(query, (fact_id,)) as cursor:
        job_id = cursor.lastrowid

    if commit:
        await conn.commit()

    logger.debug("Enqueued enrichment job %d for fact %d", job_id, fact_id)
    return job_id or 0
