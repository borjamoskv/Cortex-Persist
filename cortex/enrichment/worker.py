from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore

logger = logging.getLogger("cortex.enrichment")


class EnrichmentWorker:
    """Sovereign worker for processing enrichment jobs asynchronously."""

    def __init__(self, engine: Any, store: LedgerStore):
        self.engine = engine
        self.store = store
        self.queue = EnrichmentQueue(store)
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

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
                # claim_one is synchronous in EnrichmentQueue, but we keep it for now.
                # TODO: make EnrichmentQueue multi-engine/async aware if needed.
                job = self.queue.claim_one()

                if job:
                    await self._process_job(job)
                    poll_interval = 0.1  # Spin faster if we find work
                else:
                    await asyncio.sleep(poll_interval)
                    poll_interval = min(5.0, poll_interval + 0.5)  # Backoff
            except Exception:
                logger.exception("Error in EnrichmentWorker loop")
                await asyncio.sleep(5)

    async def _process_job(self, job: dict[str, Any]):
        """Process a single enrichment job."""
        job_id = job["job_id"]
        event_id = job["event_id"]
        attempts = job["attempts"]

        try:
            logger.debug("Processing enrichment for event %s (job %s)", event_id, job_id)

            # 1. Fetch event detail
            with self.store.tx() as conn:
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
            self.queue.mark_done(job_id, event_id)
            logger.info("Enrichment completed for event %s", event_id)

        except Exception as e:
            logger.error("Failed to process job %s: %s", job_id, e)
            self.queue.mark_failed(job_id, event_id, str(e), attempts)

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
