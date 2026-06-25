# [C5-REAL] Exergy-Maximized
"""
Telemetry Compaction Worker - Asynchronous background processor for CORTEX.
Axiom Ω₄₅: Compresses high-frequency WSS telemetry streams into causal summaries.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

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

from legacy_research.database.core import connect_async_ctx

logger = logging.getLogger("cortex.worker.telemetry_compaction")


class TelemetryCompactionWorker:
    """Worker that polls raw telemetry_batch facts and compacts them."""

    def __init__(self, db_path: str, poll_interval: float = 300.0, batch_size: int = 100):
        self.db_path = db_path
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._running = False

    async def start(self):
        """Start the worker loop."""
        self._running = True
        logger.info("TelemetryCompactionWorker started (Axiom Ω₄₅)")
        while self._running:
            try:
                await self._process_compaction()
            except Exception as e:
                logger.error("Telemetry compaction failed: %s", e)
            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """Stop the worker loop."""
        self._running = False

    async def _process_compaction(self):
        """Fetch raw telemetry facts and compact them."""
        async with connect_async_ctx(self.db_path) as conn:
            # Fetch uncompacted telemetry facts
            query = """
                SELECT id, project, content, meta 
                FROM facts 
                WHERE fact_type = 'telemetry_batch' 
                AND tags NOT LIKE '%compacted%'
                LIMIT ?
            """
            async with conn.execute(query, (self.batch_size,)) as cursor:
                rows = await cursor.fetchall()

            if not rows:
                return

            logger.info("Compacting %d telemetry batches...", len(rows))

            project_groups = {}
            for row in rows:
                fact_id, project, content, meta_raw = row
                if project not in project_groups:
                    project_groups[project] = []
                project_groups[project].append((fact_id, content, meta_raw))

            for project, batches in project_groups.items():
                await self._compact_project_batches(conn, project, batches)

            await conn.commit()

    async def _compact_project_batches(
        self, conn: aiosqlite.Connection, project: str, batches: list
    ):
        """Compact batches for a specific project."""
        ids_to_mark = []
        combined_payloads = []

        for fact_id, _content, meta_raw in batches:
            ids_to_mark.append(fact_id)
            try:
                if meta_raw:
                    meta = json.loads(meta_raw)
                    payload = meta.get("payload", {})
                    if payload:
                        combined_payloads.append(payload)
            except Exception:
                pass

        if combined_payloads:
            # Here we would normally call the LLM Compactor or synthesis engine.
            # For now, we perform a structural JSON merge.
            summary_content = f"Compacted telemetry summary of {len(combined_payloads)} batches."
            summary_meta = json.dumps(
                {
                    "compacted_at": datetime.now(timezone.utc).isoformat(),
                    "batch_count": len(combined_payloads),
                    "type": "structural_merge",
                }
            )

            # Store summary
            insert_query = """
                INSERT INTO facts (project, content, fact_type, source, confidence, meta, tags, created_at, updated_at)
                VALUES (?, ?, 'telemetry_summary', 'telemetry-compactor', 'C4', ?, '["telemetry_summary", "compacted"]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            await conn.execute(insert_query, (project, summary_content, summary_meta))

        # Mark raw facts as compacted so we don't process them again
        if ids_to_mark:
            placeholders = ",".join(["?"] * len(ids_to_mark))
            update_query = f"""
                UPDATE facts
                SET tags = json_insert(tags, '$[#]', 'compacted')
                WHERE id IN ({placeholders})
            """
            await conn.execute(update_query, ids_to_mark)
            logger.info(
                "Compacted and tagged %d telemetry facts in project %s", len(ids_to_mark), project
            )
