"""
Tests for cortex.enrichment.worker (EnrichmentWorker via LedgerStore + EnrichmentQueue)
────────────────────────────────────────────────────────────────────────────────────────
Coverage targets:
  - start / stop lifecycle
  - _run_loop: processes job when queue returns one, backs off when empty
  - _process_job: happy path (store tx + mark_done), missing event, enrichment dispatch
  - _enrich_fact: skips when no embeddings, delegates when available, surfaces errors
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.enrichment.worker import EnrichmentWorker

# ─── Helpers ──────────────────────────────────────────────────────────


def _make_worker(queue_jobs=None, store_row=None, engine=None):
    """Build an EnrichmentWorker with mocked dependencies."""
    store = MagicMock()
    engine = engine or MagicMock()

    # Store tx context manager returns a connection-like object
    conn_mock = MagicMock()
    if store_row is not None:
        conn_mock.execute.return_value.fetchone.return_value = {
            "payload_json": json.dumps(store_row)
        }
    else:
        conn_mock.execute.return_value.fetchone.return_value = None
    store.tx.return_value.__enter__ = MagicMock(return_value=conn_mock)
    store.tx.return_value.__exit__ = MagicMock(return_value=False)

    worker = EnrichmentWorker(engine=engine, store=store)

    # Mock the queue
    queue_jobs = queue_jobs or []
    worker.queue = MagicMock()
    job_iter = iter(queue_jobs)
    worker.queue.claim_one.side_effect = lambda: next(job_iter, None)
    worker.queue.mark_done = MagicMock()
    worker.queue.mark_failed = MagicMock()

    return worker, store, engine


# ─── Lifecycle ────────────────────────────────────────────────────────


class TestEnrichmentWorkerLifecycle:
    def test_initially_not_running(self):
        worker, _, _ = _make_worker()
        assert worker.is_running is False

    @pytest.mark.asyncio
    async def test_start_sets_is_running(self):
        worker, _, _ = _make_worker()
        # Patch _run_loop to avoid infinite loop
        with patch.object(worker, "_run_loop", new_callable=AsyncMock):
            await worker.start()
        assert worker.is_running is True

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """Calling start twice should not create a second task."""
        worker, _, _ = _make_worker()

        created_tasks = []
        original_create_task = asyncio.create_task

        def counting_create_task(coro, **kw):
            task = original_create_task(coro, **kw)
            created_tasks.append(task)
            return task

        with patch.object(worker, "_run_loop", new_callable=AsyncMock):
            with patch("asyncio.create_task", side_effect=counting_create_task):
                await worker.start()
                await worker.start()  # second call is a no-op

        # Only one task should have been scheduled
        assert len(created_tasks) == 1

    @pytest.mark.asyncio
    async def test_stop_clears_is_running(self):
        worker, _, _ = _make_worker()
        with patch.object(worker, "_run_loop", new_callable=AsyncMock):
            await worker.start()
        await worker.stop()
        assert worker.is_running is False


# ─── _process_job ─────────────────────────────────────────────────────


class TestProcessJob:
    @pytest.mark.asyncio
    async def test_marks_done_on_success(self):
        payload = {"action": "query", "metadata": {}}
        job = {"job_id": "j1", "event_id": "e1", "attempts": 0}
        worker, store, _ = _make_worker(queue_jobs=[job], store_row=payload)

        await worker._process_job(job)

        worker.queue.mark_done.assert_called_once_with("j1", "e1")
        worker.queue.mark_failed.assert_not_called()

    @pytest.mark.asyncio
    async def test_marks_failed_when_event_not_found(self):
        job = {"job_id": "j2", "event_id": "missing", "attempts": 1}
        worker, _, _ = _make_worker(store_row=None)

        await worker._process_job(job)

        worker.queue.mark_failed.assert_called_once()
        args = worker.queue.mark_failed.call_args[0]
        assert args[0] == "j2"
        assert args[1] == "missing"

    @pytest.mark.asyncio
    async def test_enrich_fact_called_for_store_action(self):
        payload = {
            "action": "store",
            "target": {"identifier": "42"},
            "metadata": {"content": "hello", "project": "p", "tenant_id": "t"},
        }
        job = {"job_id": "j3", "event_id": "e3", "attempts": 0}

        engine = MagicMock()
        engine.embeddings = MagicMock()
        engine.embeddings.enrich_fact = AsyncMock()

        worker, _, _ = _make_worker(queue_jobs=[job], store_row=payload, engine=engine)

        await worker._process_job(job)

        engine.embeddings.enrich_fact.assert_awaited_once_with(
            fact_id=42, content="hello", project="p", tenant_id="t"
        )

    @pytest.mark.asyncio
    async def test_no_enrich_for_non_store_action(self):
        payload = {"action": "search", "target": {"identifier": "7"}, "metadata": {}}
        job = {"job_id": "j4", "event_id": "e4", "attempts": 0}

        engine = MagicMock()
        engine.embeddings = MagicMock()
        engine.embeddings.enrich_fact = AsyncMock()

        worker, _, _ = _make_worker(queue_jobs=[job], store_row=payload, engine=engine)
        await worker._process_job(job)

        engine.embeddings.enrich_fact.assert_not_awaited()


# ─── _enrich_fact ─────────────────────────────────────────────────────


class TestEnrichFact:
    @pytest.mark.asyncio
    async def test_no_op_when_engine_has_no_embeddings(self):
        engine = MagicMock(spec=[])  # no embeddings attr
        worker, _, _ = _make_worker(engine=engine)
        # Should not raise
        await worker._enrich_fact("10", {"metadata": {"content": "x", "project": "p"}})

    @pytest.mark.asyncio
    async def test_skips_when_no_content(self):
        engine = MagicMock()
        engine.embeddings = MagicMock()
        engine.embeddings.enrich_fact = AsyncMock()
        worker, _, _ = _make_worker(engine=engine)

        await worker._enrich_fact(
            "5", {"metadata": {"content": "", "project": "p", "tenant_id": "t"}}
        )

        engine.embeddings.enrich_fact.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_enrichment_failure_is_re_raised(self):
        engine = MagicMock()
        engine.embeddings = MagicMock()
        engine.embeddings.enrich_fact = AsyncMock(side_effect=RuntimeError("embedding down"))
        worker, _, _ = _make_worker(engine=engine)

        with pytest.raises(RuntimeError, match="embedding down"):
            await worker._enrich_fact(
                "1",
                {"metadata": {"content": "hello", "project": "p", "tenant_id": "t"}},
            )


# ─── _run_loop backoff ────────────────────────────────────────────────


class TestRunLoopBackoff:
    @pytest.mark.asyncio
    async def test_loop_stops_when_is_running_false(self):
        worker, _, _ = _make_worker()
        worker.is_running = False

        # Should return immediately without hanging
        await asyncio.wait_for(worker._run_loop(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_loop_processes_one_job_then_stops(self):
        """The loop should stop once is_running is False after processing one job."""
        worker, _, _ = _make_worker()
        worker.is_running = True  # _run_loop checks while self.is_running
        processed = []
        job = {"job_id": "x", "event_id": "e", "attempts": 0}

        call_count = 0

        def controlled_claim():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return job
            worker.is_running = False
            return None

        worker.queue.claim_one.side_effect = controlled_claim

        async def intercepting_process(j):
            processed.append(j)

        worker._process_job = intercepting_process

        await asyncio.wait_for(worker._run_loop(), timeout=2.0)
        assert len(processed) == 1
