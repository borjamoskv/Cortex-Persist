# [C5-REAL] Exergy-Maximized
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
import pytest

from babylon60.database.schema import ALL_SCHEMA
from babylon60.engine import CortexEngine


@pytest.fixture
async def engine(tmp_path):
    db_path = tmp_path / "test_cortex.db"
    e = CortexEngine(db_path=str(db_path))
    await e.init_db()
    yield e
    await e.close()


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
    async with (
        aiosqlite.connect(str(engine._db_path)) as db,
        db.execute(
            "SELECT fact_id, status FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)
        ) as cursor,
    ):
        row = await cursor.fetchone()
        assert row is not None
        assert row[1] == "pending"


@pytest.mark.asyncio
async def test_worker_processing(engine):
    """Verify that the EnrichmentWorker can process a pending job."""
    from babylon60.embeddings.provider import NullEmbeddingProvider
    from babylon60.worker.enrichment import EnrichmentWorker

    # Store a fact
    fact_id = await engine.store(
        project="test_project", content="Job processing test", source="worker_test"
    )

    # Initialize worker with Null provider (Survival mode)
    worker = EnrichmentWorker(db_path=str(engine._db_path), provider=NullEmbeddingProvider())

    # Process one job
    async with (
        aiosqlite.connect(str(engine._db_path)) as db,
        db.execute(
            "SELECT id, fact_id FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)
        ) as cursor,
    ):
        job = await cursor.fetchone()
        # SQLite row indexing: id[0], fact_id[1]
        await worker._process_job(db, job[0], job[1])
        await db.commit()

    # Verify job status is updated to completed
    async with (
        aiosqlite.connect(str(engine._db_path)) as db,
        db.execute("SELECT status FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)) as cursor,
    ):
        row = await cursor.fetchone()
        assert row[0] == "completed"
