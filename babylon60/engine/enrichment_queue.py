# [C5-REAL] Exergy-Maximized
"""
Enrichment Queue management for P0 Decoupling.
"""

from __future__ import annotations

import logging

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

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
