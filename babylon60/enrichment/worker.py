# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from babylon60.ledger.queue import EnrichmentQueue
from babylon60.ledger.store import LedgerStore

logger = logging.getLogger("cortex.enrichment")


class EnrichmentWorker:
    """Sovereign worker for processing enrichment jobs asynchronously."""

    def __init__(self, engine: Any, store: LedgerStore | Any):
        self.engine = engine
        self.is_running = False
        self._task: asyncio.Task | None = None
        self._compat_db_mode = not hasattr(store, "tx")

        if self._compat_db_mode:
            self.store = None
            self.queue = None
            self._db_path = getattr(store, "DB_PATH", getattr(engine, "_db_path", None))
        else:
            self.store = store
            self.queue = EnrichmentQueue(store)
            self._db_path = None

    async def start(self):
        """Start the background worker."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("EnrichmentWorker started.")

    async def stop(self):
        """Stop the background worker."""
        self.is_running = False
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
        logger.info("EnrichmentWorker stopped.")

    async def _run_loop(self):
        """Main worker loop with adaptive polling."""
        poll_interval = 1.0
        while self.is_running:
            try:
                if self._compat_db_mode:
                    job = await self._get_next_job()
                else:
                    # Polling from EnrichmentQueue is currently synchronous to ensure
                    # atomic claim operations within the underlying SQLite transaction.
                    job = self.queue.claim_one()  # type: ignore[reportOptionalMemberAccess]

                if job:
                    await self._process_job(job)
                    poll_interval = 0.1  # Spin faster if we find work
                else:
                    await asyncio.sleep(poll_interval)
                    poll_interval = min(5.0, poll_interval + 0.5)  # Backoff
            except (RuntimeError, ValueError, OSError):
                logger.exception("Error in EnrichmentWorker loop")
                await asyncio.sleep(5)

    async def _get_next_job(self) -> dict[str, Any] | None:
        """Compatibility path for legacy enrichment_jobs-backed workers."""
        if not self._compat_db_mode:
            return self.queue.claim_one()  # type: ignore[reportOptionalMemberAccess]

        now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                """
                SELECT id, fact_id, attempts
                FROM enrichment_jobs
                WHERE status IN ('pending', 'queued', 'failed')
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY id
                LIMIT 1
                """,
                (now,),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return {
            "job_id": row[0],
            "fact_id": row[1],
            "attempts": row[2] or 0,
        }

    async def _process_job(self, job: dict[str, Any]):
        """Process a single enrichment job."""
        if self._compat_db_mode:
            await self._process_queued_job(job)
            return

        job_id = job["job_id"]
        event_id = job["event_id"]
        attempts = job["attempts"]

        try:
            logger.debug("Processing enrichment for event %s (job %s)", event_id, job_id)

            # 1. Fetch event detail
            with self.store.tx() as conn:  # type: ignore[reportOptionalMemberAccess]
                row = conn.execute(
                    "SELECT payload_json FROM ledger_events WHERE event_id=?", (event_id,)
                ).fetchone()
                if not row:
                    raise ValueError(f"Event {event_id} not found in ledger")
                payload = json.loads(row["payload_json"])

            # 2. Perform enrichment based on action/tool
            # For now, default to generating embedding if it looks like a fact
            if payload.get("action") in ("store", "create", "update"):
                target = payload.get("target", {})
                if target.get("identifier"):  # Likely a fact ID
                    await self._enrich_fact(target["identifier"], payload)

            # 3. Mark successful
            self.queue.mark_done(job_id, event_id)  # type: ignore[reportOptionalMemberAccess]
            logger.info("Enrichment completed for event %s", event_id)

        except Exception as e:
            logger.error("Failed to process job %s: %s", job_id, e)
            self.queue.mark_failed(job_id, event_id, str(e), attempts)  # type: ignore[reportOptionalMemberAccess]

    async def _process_queued_job(self, job: dict[str, Any]) -> None:
        """Process a legacy enrichment_jobs row for backward compatibility."""
        job_id = int(job["job_id"])
        fact_id = int(job["fact_id"])

        try:
            async with self.engine.session() as conn:
                cursor = await conn.execute(
                    "SELECT project, content, tenant_id FROM facts WHERE id = ?",
                    (fact_id,),
                )
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Fact {fact_id} not found")

                project, content, tenant_id = row
                if hasattr(self.engine, "embeddings") and getattr(self.engine, "embeddings", None):
                    await self.engine.embeddings.enrich_fact(
                        fact_id=fact_id,
                        content=content,
                        project=project,
                        tenant_id=tenant_id,
                    )

                await conn.execute(
                    """
                    UPDATE enrichment_jobs
                    SET status = 'completed', updated_at = ?
                    WHERE id = ?
                    """,
                    (datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(), job_id),
                )
                await conn.commit()
        except Exception as e:
            async with self.engine.session() as conn:
                await conn.execute(
                    """
                    UPDATE enrichment_jobs
                    SET status = 'failed',
                        attempts = attempts + 1,
                        last_error = ?,
                        next_attempt_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        str(e),
                        (
                            datetime.fromtimestamp(time.time(), tz=timezone.utc)
                            + timedelta(minutes=5)
                        ).isoformat(),
                        datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                        job_id,
                    ),
                )
                await conn.commit()
            raise

    async def _enrich_fact(self, fact_id: str | int, payload: dict[str, Any]):
        """Generate embeddings or summaries for a fact."""
        # This uses the engine to perform the heavy lifting
        if not hasattr(self.engine, "embeddings"):
            return

        try:
            # Metadata usually contains 'content' and 'project'
            metadata = payload.get("metadata", {})
            content = metadata.get("content", "")
            project = metadata.get("project", "default")
            tenant_id = metadata.get("tenant_id", "default")

            if not content:
                logger.warning("No content found for fact %s enrichment", fact_id)
                return

            # Call the sovereign enrichment method in EmbeddingManager
            await self.engine.embeddings.enrich_fact(
                fact_id=int(fact_id), content=content, project=project, tenant_id=tenant_id
            )
        except Exception as e:
            logger.warning("Semantic enrichment for fact %s failure: %s", fact_id, e)
            raise
