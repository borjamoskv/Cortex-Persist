"""Enrichment Worker — Background semantic enrichment.

Axiom Ω₁₃: An optional subsystem must not degrade base truth persistence.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from cortex.engine.capabilities import CapabilityRegistry

logger = logging.getLogger("cortex.enrichment")


async def run_enrichment_worker(engine: Any, poll_interval: float = 1.0):
    """Background loop to process enrichment jobs."""
    logger.info("Enrichment Worker started (Ω₁₃).")

    while True:
        try:
            processed = await process_next_job(engine)
            if not processed:
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Enrichment Worker critical failure: %s", e)
            await asyncio.sleep(5)


async def process_next_job(engine: Any) -> bool:
    """Fetch and process the oldest queued job."""
    caps = CapabilityRegistry.get_instance().capabilities
    if not caps.embeddings:
        return False

    async with engine.session() as conn:
        # P0: SQLite + WAL with polling
        # Find next queued or retryable job
        query = """
            SELECT j.id, j.fact_id, f.content, f.project, f.tenant_id, j.attempts
            FROM enrichment_jobs j
            JOIN facts f ON j.fact_id = f.id
            WHERE j.status = 'pending' 
               OR (j.status = 'failed' AND j.attempts < 5 AND j.next_attempt_at < datetime('now'))
            ORDER BY j.created_at ASC
            LIMIT 1
        """
        async with conn.execute(query) as cursor:
            job = await cursor.fetchone()

        if not job:
            return False

        job_id, fact_id, content, project, tenant_id, attempts = job[0:6]

        # Mark as processing
        await conn.execute(
            "UPDATE enrichment_jobs SET status = 'processing', updated_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
        await conn.commit()

        try:
            logger.debug(
                "Processing enrichment for fact %d (job %d, attempt %d)",
                fact_id,
                job_id,
                attempts + 1,
            )

            # Actual enrichment via engine.embeddings.enrich_fact
            await engine.embeddings.enrich_fact(fact_id, content, project, tenant_id)

            # Success
            await conn.execute(
                "UPDATE facts SET semantic_status = 'indexed' WHERE id = ?", (fact_id,)
            )
            await conn.execute("DELETE FROM enrichment_jobs WHERE id = ?", (job_id,))
            await conn.commit()
            return True

        except Exception as e:
            logger.warning("Enrichment job %d failed: %s", job_id, e)
            attempts += 1
            # Exponential backoff: 60s, 120s, 240s, 480s, 960s...
            delay_sec = 60 * (2 ** (attempts - 1))

            await conn.execute(
                """UPDATE enrichment_jobs 
                   SET status = 'failed', 
                       attempts = ?, 
                       last_error = ?, 
                       next_attempt_at = datetime('now', ?),
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (attempts, str(e), f"+{delay_sec} seconds", job_id),
            )
            await conn.execute(
                "UPDATE facts SET semantic_status = 'failed', semantic_error = ? WHERE id = ?",
                (str(e), fact_id),
            )
            await conn.commit()
            return True
