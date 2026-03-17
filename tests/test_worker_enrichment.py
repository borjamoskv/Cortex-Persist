"""
Tests for cortex.worker.enrichment (aiosqlite-backed EnrichmentWorker)
───────────────────────────────────────────────────────────────────────
Coverage targets:
  - start / stop lifecycle
  - _process_batch: query construction, job dispatch
  - _process_job: happy path (mark_success), missing fact (mark_failure),
    provider invocation gate (provider is None vs present)
  - _mark_success / _mark_failure: SQL correctness, exponential backoff timestamp
  - LLM provider gate: ⚠️  Only if CORTEX_LLM_PROVIDER configured

Uses an in-memory aiosqlite database to avoid file side-effects.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest

from cortex.worker.enrichment import EnrichmentWorker

# ─── Schema helpers ───────────────────────────────────────────────────

_CREATE_FACTS = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    project TEXT NOT NULL,
    content TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default'
)
"""

_CREATE_JOBS = """
CREATE TABLE IF NOT EXISTS enrichment_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    next_attempt_at TEXT,
    updated_at TEXT
)
"""


async def _setup_db() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute(_CREATE_FACTS)
    await conn.execute(_CREATE_JOBS)
    await conn.commit()
    return conn


# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def worker(tmp_path):
    """Worker pointing at a temp SQLite file (real DB, controlled schema)."""
    db_path = str(tmp_path / "test_worker.db")
    return EnrichmentWorker(db_path=db_path, provider=None, poll_interval=0.05)


@pytest.fixture
def worker_with_provider(tmp_path):
    provider = MagicMock()
    provider.is_available.return_value = True
    db_path = str(tmp_path / "test_worker_prov.db")
    return EnrichmentWorker(db_path=db_path, provider=provider, poll_interval=0.05)


# ─── Lifecycle ────────────────────────────────────────────────────────


class TestWorkerLifecycle:
    def test_initial_state(self, worker):
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_stop_before_start_is_safe(self, worker):
        await worker.stop()
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_start_and_stop(self, worker):
        """start() sets _running; stop() clears it."""
        with patch.object(worker, "_process_batch", new_callable=AsyncMock):
            task = asyncio.create_task(worker.start())
            await asyncio.sleep(0.15)  # let one iteration run
            await worker.stop()
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()
        assert worker._running is False


# ─── _mark_success ────────────────────────────────────────────────────


class TestMarkSuccess:
    @pytest.mark.asyncio
    async def test_sets_status_completed(self, worker):
        conn = await _setup_db()
        await conn.execute(
            "INSERT INTO enrichment_jobs (fact_id, status) VALUES (?, ?)", (1, "queued")
        )
        await conn.commit()

        async with conn.execute("SELECT id FROM enrichment_jobs") as cur:
            job = await cur.fetchone()

        await worker._mark_success(conn, job["id"])
        await conn.commit()

        async with conn.execute(
            "SELECT status FROM enrichment_jobs WHERE id=?", (job["id"],)
        ) as cur:
            row = await cur.fetchone()
        assert row["status"] == "completed"
        await conn.close()


# ─── _mark_failure ────────────────────────────────────────────────────


class TestMarkFailure:
    @pytest.mark.asyncio
    async def test_increments_attempts_and_sets_error(self, worker):
        conn = await _setup_db()
        await conn.execute(
            "INSERT INTO enrichment_jobs (fact_id, status, attempts) VALUES (?, ?, ?)",
            (2, "queued", 0),
        )
        await conn.commit()

        async with conn.execute("SELECT id FROM enrichment_jobs") as cur:
            job = await cur.fetchone()
        job_id = job["id"]

        await worker._mark_failure(conn, job_id, "Test error")
        await conn.commit()

        async with conn.execute(
            "SELECT status, attempts, last_error, next_attempt_at FROM enrichment_jobs WHERE id=?",
            (job_id,),
        ) as cur:
            row = await cur.fetchone()

        assert row["status"] == "failed"
        assert row["attempts"] == 1
        assert row["last_error"] == "Test error"
        # next_attempt_at should be ~5 minutes from now
        next_dt = datetime.fromisoformat(row["next_attempt_at"])
        assert next_dt > datetime.now() + timedelta(minutes=4)
        await conn.close()


# ─── _process_job ─────────────────────────────────────────────────────


class TestProcessJob:
    @pytest.mark.asyncio
    async def test_marks_success_when_fact_found(self, worker):
        conn = await _setup_db()
        await conn.execute(
            "INSERT INTO facts (id, project, content, tenant_id) VALUES (?, ?, ?, ?)",
            (10, "proj", "hello world", "tenant1"),
        )
        await conn.execute(
            "INSERT INTO enrichment_jobs (fact_id, status) VALUES (?, ?)", (10, "queued")
        )
        await conn.commit()

        async with conn.execute("SELECT id FROM enrichment_jobs WHERE fact_id=10") as cur:
            job = await cur.fetchone()

        with patch.object(worker, "_mark_success", new_callable=AsyncMock) as mock_success:
            await worker._process_job(conn, job["id"], 10)
            mock_success.assert_awaited_once_with(conn, job["id"])

        await conn.close()

    @pytest.mark.asyncio
    async def test_marks_failure_when_fact_missing(self, worker):
        conn = await _setup_db()
        await conn.execute(
            "INSERT INTO enrichment_jobs (fact_id, status) VALUES (?, ?)", (999, "queued")
        )
        await conn.commit()

        async with conn.execute("SELECT id FROM enrichment_jobs WHERE fact_id=999") as cur:
            job = await cur.fetchone()

        with patch.object(worker, "_mark_failure", new_callable=AsyncMock) as mock_fail:
            await worker._process_job(conn, job["id"], 999)
            mock_fail.assert_awaited_once()
            args = mock_fail.call_args[0]
            assert "999" in args[2]  # error message mentions fact id

        await conn.close()

    @pytest.mark.asyncio
    async def test_provider_invocation_gated(self, worker_with_provider):
        """Provider path is guarded by is_available — log and pass for now."""
        conn = await _setup_db()
        await conn.execute(
            "INSERT INTO facts (id, project, content, tenant_id) VALUES (?, ?, ?, ?)",
            (20, "proj", "content", "t"),
        )
        await conn.execute(
            "INSERT INTO enrichment_jobs (fact_id, status) VALUES (?, ?)", (20, "queued")
        )
        await conn.commit()

        async with conn.execute("SELECT id FROM enrichment_jobs WHERE fact_id=20") as cur:
            job = await cur.fetchone()

        with patch.object(worker_with_provider, "_mark_success", new_callable=AsyncMock) as mock_ok:
            await worker_with_provider._process_job(conn, job["id"], 20)
            # Provider is injected but current impl just passes — success should still be marked
            mock_ok.assert_awaited_once()

        await conn.close()

    @pytest.mark.asyncio
    async def test_no_provider_still_succeeds(self, worker):
        """Without a provider, job still completes (no embedding, no crash)."""
        conn = await _setup_db()
        await conn.execute(
            "INSERT INTO facts (id, project, content, tenant_id) VALUES (?, ?, ?, ?)",
            (30, "p", "data", "t"),
        )
        await conn.execute(
            "INSERT INTO enrichment_jobs (fact_id, status) VALUES (?, ?)", (30, "queued")
        )
        await conn.commit()

        async with conn.execute("SELECT id FROM enrichment_jobs WHERE fact_id=30") as cur:
            job = await cur.fetchone()

        with patch.object(worker, "_mark_success", new_callable=AsyncMock) as mock_ok:
            await worker._process_job(conn, job["id"], 30)
            mock_ok.assert_awaited_once()

        await conn.close()


# ─── _process_batch integration ───────────────────────────────────────


class TestProcessBatch:
    @pytest.mark.asyncio
    async def test_batch_picks_queued_jobs(self, worker, tmp_path):
        """Full round-trip: insert jobs, run batch, verify statuses updated."""
        import aiosqlite as _aio

        db_path = str(tmp_path / "batch.db")
        async with _aio.connect(db_path) as conn:
            conn.row_factory = _aio.Row
            await conn.execute(_CREATE_FACTS)
            await conn.execute(_CREATE_JOBS)
            await conn.execute(
                "INSERT INTO facts (id, project, content, tenant_id) VALUES (1, 'p', 'hello', 't')"
            )
            await conn.execute("INSERT INTO enrichment_jobs (fact_id, status) VALUES (1, 'queued')")
            await conn.commit()

        # Patch the worker's db_path
        worker.db_path = db_path
        await worker._process_batch(batch_size=5)

        async with _aio.connect(db_path) as conn:
            conn.row_factory = _aio.Row
            async with conn.execute("SELECT status FROM enrichment_jobs WHERE fact_id=1") as cur:
                row = await cur.fetchone()
            assert row["status"] == "completed"

    @pytest.mark.asyncio
    async def test_failed_jobs_retried_after_backoff(self, worker, tmp_path):
        """Jobs with status='failed' and past next_attempt_at should be re-picked."""
        import aiosqlite as _aio

        db_path = str(tmp_path / "retry.db")
        past = (datetime.now() - timedelta(minutes=10)).isoformat()
        async with _aio.connect(db_path) as conn:
            conn.row_factory = _aio.Row
            await conn.execute(_CREATE_FACTS)
            await conn.execute(_CREATE_JOBS)
            await conn.execute(
                "INSERT INTO facts (id, project, content, tenant_id) VALUES (5, 'p', 'retry me', 't')"
            )
            await conn.execute(
                "INSERT INTO enrichment_jobs (fact_id, status, next_attempt_at, attempts) VALUES (5, 'failed', ?, 1)",
                (past,),
            )
            await conn.commit()

        worker.db_path = db_path
        await worker._process_batch(batch_size=5)

        async with _aio.connect(db_path) as conn:
            conn.row_factory = _aio.Row
            async with conn.execute("SELECT status FROM enrichment_jobs WHERE fact_id=5") as cur:
                row = await cur.fetchone()
            assert row["status"] == "completed"
