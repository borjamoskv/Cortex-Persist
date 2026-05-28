import aiosqlite
import pytest

from cortex.database.schema import ALL_SCHEMA
from cortex.engine import CortexEngine


@pytest.fixture
async def engine(tmp_path):
    import sqlite_vec

    db_path = tmp_path / "test_cortex.db"
    engine = CortexEngine(db_path=str(db_path))
    # Initialize schema with extension loaded
    async with aiosqlite.connect(str(db_path)) as db:
        await db.enable_load_extension(True)
        await db.load_extension(sqlite_vec.loadable_path())
        await db.enable_load_extension(False)
        for statement in ALL_SCHEMA:
            await db.executescript(statement)
        await db.commit()
    return engine


@pytest.mark.asyncio
async def test_store_decoupled(engine):
    """Verify that store() persists the fact and enqueues an enrichment job."""
    fact_id = await engine.store(
        project="test_project",
        content="Worker test fact",
        meta={"worker_test": True},
        source="test_suite",
    )

    assert fact_id is not None

    # Check that the fact is in the facts table (using engine.retrieve for decryption)
    fact = await engine.retrieve(fact_id)
    assert fact.content == "Worker test fact"

    # Check that a job is in the enrichment_jobs table
    async with aiosqlite.connect(str(engine._db_path)) as db:
        async with db.execute(
            "SELECT fact_id, status FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row[1] == "pending"


@pytest.mark.asyncio
async def test_worker_processing(engine):
    """Verify that the EnrichmentWorker can process a pending job."""
    from cortex.embeddings.provider import NullEmbeddingProvider
    from cortex.worker.enrichment import EnrichmentWorker

    # Store a fact
    fact_id = await engine.store(
        project="test_project", content="Job processing test", source="worker_test"
    )

    # Initialize worker with Null provider (Survival mode)
    worker = EnrichmentWorker(db_path=str(engine._db_path), provider=NullEmbeddingProvider())

    # Process one job
    async with aiosqlite.connect(str(engine._db_path)) as db:
        async with db.execute(
            "SELECT id, fact_id FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)
        ) as cursor:
            job = await cursor.fetchone()
            # SQLite row indexing: id[0], fact_id[1]
            await worker._process_job(db, job[0], job[1])
            await db.commit()

    # Verify job status is updated to completed
    async with aiosqlite.connect(str(engine._db_path)) as db:
        async with db.execute(
            "SELECT status FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row[0] == "completed"
