import pytest
import os
import sqlite3
import aiosqlite
import asyncio
from datetime import datetime, timezone

from cortex.engine.causal.taint_engine import (
    generate_taint_token,
    TaintValidationError,
    verify_taint_token,
)
from cortex.engine.fact_store_core import insert_fact_record
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import MemoryEvent, CortexFactModel
from cortex.memory.hdc.store import HDCVectorStoreL2
from cortex.memory.hdc.codec import HDCEncoder
from cortex.memory.hdc.item_memory import ItemMemory
from cortex.memory.traits.write import WriteTrait

# Set environment variable to enable verification in tests
@pytest.fixture(autouse=True)
def enable_taint_verification():
    os.environ["CORTEX_NO_TAINT_ENFORCE"] = "0"
    yield
    os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"

@pytest.fixture
def clean_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    # Initialize basic schema for tests
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            project TEXT,
            content TEXT,
            fact_type TEXT,
            metadata TEXT,
            hash TEXT,
            source TEXT,
            confidence TEXT,
            confidence_rank INTEGER,
            consensus_score REAL,
            relation_type TEXT,
            quadrant TEXT,
            storage_tier TEXT,
            exergy_score REAL,
            category TEXT,
            yield_score REAL,
            semantic_status TEXT,
            tags TEXT,
            tx_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            valid_from TEXT
        )
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS enrichment_jobs (fact_id INTEGER, job_type TEXT, status TEXT, priority INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS fact_tags (fact_id INTEGER, tag TEXT, tenant_id TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS facts_fts (rowid INTEGER, content TEXT, project TEXT, tags TEXT, fact_type TEXT, tenant_id TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS causal_edges (fact_id INTEGER, parent_id INTEGER, signal_id TEXT, edge_type TEXT, project TEXT, tenant_id TEXT)")
    yield conn
    conn.close()

@pytest.mark.asyncio
async def test_fact_store_core_taint_rejection(clean_db):
    """Verifies fact_store_core insert_fact_record rejects missing/invalid tokens."""
    # Convert sqlite3 connection to aiosqlite-like interface for testing
    async def run_test():
        async with aiosqlite.connect(":memory:") as aio_conn:
            # Recreate facts schema in temp aio_conn
            await aio_conn.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, tenant_id TEXT, content TEXT, fact_type TEXT)")
            
            # Missing token
            with pytest.raises(TaintValidationError):
                await insert_fact_record(
                    aio_conn,
                    tenant_id="default",
                    project="default",
                    content="Hello world",
                    fact_type="general",
                    tags=None,
                    confidence="C5",
                    ts=None,
                    source=None,
                    meta=None,
                    tx_id=None
                )
                
            # Invalid token format
            with pytest.raises(TaintValidationError):
                await insert_fact_record(
                    aio_conn,
                    tenant_id="default",
                    project="default",
                    content="Hello world",
                    fact_type="general",
                    tags=None,
                    confidence="C5",
                    ts=None,
                    source=None,
                    meta={"cortex_taint": "invalid_format_token"},
                    tx_id=None
                )

            # Valid token
            valid_token = generate_taint_token("agent_1", "session_123", "Hello world")
            fact_id = await insert_fact_record(
                aio_conn,
                tenant_id="default",
                project="default",
                content="Hello world",
                fact_type="general",
                tags=None,
                confidence="C5",
                ts=None,
                source=None,
                meta={"cortex_taint": valid_token},
                tx_id=None
            )
            assert fact_id > 0

    await run_test()

@pytest.mark.asyncio
async def test_event_ledger_l3_taint_rejection():
    """Verifies EventLedgerL3 rejects missing/invalid tokens."""
    async with aiosqlite.connect(":memory:") as conn:
        ledger = EventLedgerL3(conn)
        
        # Missing token
        ev_missing = MemoryEvent(
            role="user",
            content="Hello L3",
            token_count=10,
            session_id="sess_1",
            tenant_id="default"
        )
        with pytest.raises(TaintValidationError):
            await ledger.append_event(ev_missing)

        # Invalid token
        ev_invalid = MemoryEvent(
            role="user",
            content="Hello L3",
            token_count=10,
            session_id="sess_1",
            tenant_id="default",
            metadata={"cortex_taint": "taint:agent:session:2026-06-06T10:00:00:wronghash"}
        )
        with pytest.raises(TaintValidationError):
            await ledger.append_event(ev_invalid)

        # Valid token
        valid_token = generate_taint_token("agent_1", "session_1", "Hello L3")
        ev_valid = MemoryEvent(
            role="user",
            content="Hello L3",
            token_count=10,
            session_id="sess_1",
            tenant_id="default",
            metadata={"cortex_taint": valid_token}
        )
        # Should succeed
        await ledger.append_event(ev_valid)

@pytest.mark.asyncio
async def test_hdc_store_l2_taint_rejection(tmp_path):
    """Verifies HDCVectorStoreL2 rejects missing/invalid tokens."""
    item_mem = ItemMemory(dim=128)
    encoder = HDCEncoder(item_mem)
    db_file = tmp_path / "hdc.db"
    
    store = HDCVectorStoreL2(encoder, item_mem, db_path=db_file)
    
    # Missing token
    fact_missing = CortexFactModel(
        tenant_id="default",
        project_id="default",
        content="HDC Fact",
        embedding=[0.1]*128,
        metadata={}
    )
    with pytest.raises(TaintValidationError):
        await store.memorize(fact_missing)
        
    # Invalid token
    fact_invalid = CortexFactModel(
        tenant_id="default",
        project_id="default",
        content="HDC Fact",
        embedding=[0.1]*128,
        metadata={"cortex_taint": "taint:agent:session:2026-06-06T10:00:00:wronghash"}
    )
    with pytest.raises(TaintValidationError):
        await store.memorize(fact_invalid)

    # Valid token
    valid_token = generate_taint_token("agent_1", "session_1", "HDC Fact")
    fact_valid = CortexFactModel(
        tenant_id="default",
        project_id="default",
        content="HDC Fact",
        embedding=[0.1]*128,
        metadata={"cortex_taint": valid_token}
    )
    # Should succeed
    await store.memorize(fact_valid)
    await store.close()

@pytest.mark.asyncio
async def test_write_trait_taint_rejection(clean_db):
    """Verifies WriteTrait rejects missing/invalid tokens."""
    class DummyWriter(WriteTrait):
        def __init__(self, conn):
            self.conn = conn
            self._lock = asyncio.Lock()
            self._vector_enabled = False
            
        def _get_conn(self):
            return self.conn
            
        def _get_sanitizer(self):
            return None
            
        def _get_domain_tables(self, conn, tenant, project):
            # Create a mock table for domain with all required columns
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS facts_{tenant}_{project} (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    project_id TEXT,
                    content TEXT,
                    timestamp REAL,
                    is_diamond INTEGER,
                    is_bridge INTEGER,
                    confidence TEXT,
                    success_rate REAL,
                    cognitive_layer TEXT,
                    parent_decision_id INTEGER,
                    metadata TEXT,
                    exergy_score REAL,
                    category TEXT,
                    quadrant TEXT,
                    storage_tier TEXT,
                    facet_version INTEGER
                )
            """)
            return (f"facts_{tenant}_{project}", None, None, None)

    writer = DummyWriter(clean_db)
    
    # Missing token
    fact_missing = CortexFactModel(
        tenant_id="def",
        project_id="proj",
        content="WriteTrait Fact",
        embedding=[0.1]*384,
        metadata={}
    )
    with pytest.raises(TaintValidationError):
        await writer.memorize(fact_missing)
        
    # Invalid token
    fact_invalid = CortexFactModel(
        tenant_id="def",
        project_id="proj",
        content="WriteTrait Fact",
        embedding=[0.1]*384,
        metadata={"cortex_taint": "taint:agent:session:2026-06-06T10:00:00:wronghash"}
    )
    with pytest.raises(TaintValidationError):
        await writer.memorize(fact_invalid)
        
    # Valid token
    valid_token = generate_taint_token("agent_1", "session_1", "WriteTrait Fact")
    fact_valid = CortexFactModel(
        tenant_id="def",
        project_id="proj",
        content="WriteTrait Fact",
        embedding=[0.1]*384,
        metadata={"cortex_taint": valid_token}
    )
    # Should succeed
    await writer.memorize(fact_valid)

