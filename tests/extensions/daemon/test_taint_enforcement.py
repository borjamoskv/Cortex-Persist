# [C5-REAL] Exergy-Maximized
import pytest
import hashlib
import os
import sqlite3
import aiosqlite
import asyncio
import base64
import time
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
    PublicFormat,
)

from cortex.engine.causal.taint_engine import (
    generate_secure_taint_token,
    TaintValidationError,
    verify_taint_token,
    canonicalize_content,
)
from cortex.engine.causal.verification_oracle import (
    verify_c5_state_machine,
    InvariantViolationError,
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
def agent_keys():
    priv = Ed25519PrivateKey.generate()
    priv_b64 = base64.b64encode(
        priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    ).decode("ascii")
    pub_b64 = base64.b64encode(
        priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")
    return priv_b64, pub_b64


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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, name TEXT, agent_type TEXT, reputation_score REAL, public_key TEXT, tenant_id TEXT, is_active INTEGER DEFAULT 1)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS enrichment_jobs (fact_id INTEGER, job_type TEXT, status TEXT, priority INTEGER)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS fact_tags (fact_id INTEGER, tag TEXT, tenant_id TEXT)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS facts_fts (rowid INTEGER, content TEXT, project TEXT, tags TEXT, fact_type TEXT, tenant_id TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS causal_edges (fact_id INTEGER, parent_id INTEGER, signal_id TEXT, edge_type TEXT, project TEXT, tenant_id TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS auth_requests (id TEXT PRIMARY KEY, hypothesis TEXT, state_payload TEXT, status TEXT, created_at REAL, resolved_at REAL, signature TEXT, public_key TEXT)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS taint_nonces (nonce TEXT PRIMARY KEY, timestamp REAL)")
    yield conn
    conn.close()


async def setup_aio_db(aio_conn, agent_id, pub_key):
    await aio_conn.execute("""
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
    await aio_conn.execute(
        "CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, name TEXT, agent_type TEXT, reputation_score REAL, public_key TEXT, tenant_id TEXT, is_active INTEGER DEFAULT 1)"
    )
    await aio_conn.execute(
        "CREATE TABLE IF NOT EXISTS enrichment_jobs (fact_id INTEGER, job_type TEXT, status TEXT, priority INTEGER)"
    )
    await aio_conn.execute(
        "CREATE TABLE IF NOT EXISTS fact_tags (fact_id INTEGER, tag TEXT, tenant_id TEXT)"
    )
    await aio_conn.execute(
        "CREATE TABLE IF NOT EXISTS facts_fts (rowid INTEGER, content TEXT, project TEXT, tags TEXT, fact_type TEXT, tenant_id TEXT)"
    )
    await aio_conn.execute(
        "CREATE TABLE IF NOT EXISTS causal_edges (fact_id INTEGER, parent_id INTEGER, signal_id TEXT, edge_type TEXT, project TEXT, tenant_id TEXT)"
    )
    await aio_conn.execute(
        "CREATE TABLE IF NOT EXISTS auth_requests (id TEXT PRIMARY KEY, hypothesis TEXT, state_payload TEXT, status TEXT, created_at REAL, resolved_at REAL, signature TEXT, public_key TEXT)"
    )
    await aio_conn.execute(
        "CREATE TABLE IF NOT EXISTS taint_nonces (nonce TEXT PRIMARY KEY, timestamp REAL)"
    )

    # Register test agent
    await aio_conn.execute(
        "INSERT INTO agents (id, name, agent_type, reputation_score, public_key, tenant_id) VALUES (?, ?, ?, 1.0, ?, 'default')",
        (agent_id, "TestAgent", "ai", pub_key),
    )
    await aio_conn.commit()


@pytest.mark.asyncio
async def test_fact_store_core_taint_rejection(agent_keys):
    """Verifies fact_store_core insert_fact_record rejects missing/invalid tokens."""
    priv, pub = agent_keys
    agent_id = "agent_1"

    async with aiosqlite.connect(":memory:") as aio_conn:
        await setup_aio_db(aio_conn, agent_id, pub)

        # 1. Missing token
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
                tx_id=None,
            )

        # 2. Invalid token format
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
                tx_id=None,
            )

        # 3. Valid token (succeeds)
        valid_token = generate_secure_taint_token(agent_id, "session_123", "Hello world", priv)
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
            tx_id=None,
        )
        assert fact_id > 0

        # 4. Replay attack (reuse same token/nonce, must fail)
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
                meta={"cortex_taint": valid_token},
                tx_id=None,
            )


@pytest.mark.asyncio
async def test_store_mixin_taint_rejection_precedes_transaction(agent_keys, tmp_path):
    """StoreMixin must reject missing taint before appending to the transaction ledger."""
    _priv, pub = agent_keys
    from cortex.engine import CortexEngine

    db_path = tmp_path / "store_taint.db"
    engine = CortexEngine(db_path=str(db_path), auto_embed=False)
    await engine.init_db()
    try:
        async with engine.session() as conn:
            await conn.execute(
                "INSERT INTO agents (id, name, agent_type, reputation_score, public_key, tenant_id) "
                "VALUES (?, ?, ?, 1.0, ?, 'default')",
                ("agent_1", "TestAgent", "ai", pub),
            )
            await conn.commit()

        with pytest.raises(TaintValidationError):
            await engine.store(
                project="default",
                content="StoreMixin rejects this fact before writing a ledger transaction.",
                fact_type="knowledge",
                source="agent:test_suite",
                meta={},
            )

        async with engine.session() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
            row = await cursor.fetchone()
            assert row[0] == 0
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_store_mixin_guard_runtime_error_fails_closed(monkeypatch, tmp_path):
    """Unexpected guard failures must abort instead of being downgraded to writes."""
    from cortex.engine import CortexEngine

    db_path = tmp_path / "store_guard.db"
    engine = CortexEngine(db_path=str(db_path), auto_embed=False)
    await engine.init_db()
    try:

        async def fail_guard(*args, **kwargs):
            raise RuntimeError("guard runtime failure")

        monkeypatch.setattr(engine._guard_pipeline, "run_guards", fail_guard)
        with pytest.raises(RuntimeError, match="guard runtime failure"):
            await engine.store(
                project="default",
                content="Guard runtime failure must abort before persistence.",
                fact_type="knowledge",
                source="agent:test_suite",
                meta={},
            )

        async with engine.session() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
            row = await cursor.fetchone()
            assert row[0] == 0
    finally:
        await engine.close()


def test_storage_guard_rejects_missing_source():
    from cortex.engine.storage_guard import GuardViolation, StorageGuard

    with pytest.raises(GuardViolation, match="SOURCE_REQUIRED"):
        StorageGuard.validate(
            project="default",
            content="Source attribution is mandatory for this store proposal.",
            fact_type="knowledge",
            source=None,
            confidence="C5",
            tags=None,
            meta={},
        )


@pytest.mark.asyncio
async def test_event_ledger_l3_taint_rejection(agent_keys):
    """Verifies EventLedgerL3 rejects missing/invalid tokens."""
    priv, pub = agent_keys
    agent_id = "agent_1"

    async with aiosqlite.connect(":memory:") as conn:
        await setup_aio_db(conn, agent_id, pub)
        ledger = EventLedgerL3(conn)

        # Missing token
        ev_missing = MemoryEvent(
            role="user",
            content="Hello L3",
            token_count=10,
            session_id="sess_1",
            tenant_id="default",
        )
        with pytest.raises(TaintValidationError):
            await ledger.append_event(ev_missing)

        # Valid token
        valid_token = generate_secure_taint_token(agent_id, "session_1", "Hello L3", priv)
        ev_valid = MemoryEvent(
            role="user",
            content="Hello L3",
            token_count=10,
            session_id="sess_1",
            tenant_id="default",
            metadata={"cortex_taint": valid_token},
        )
        # Should succeed
        await ledger.append_event(ev_valid)


@pytest.mark.asyncio
async def test_hdc_store_l2_taint_rejection(tmp_path, agent_keys):
    """Verifies HDCVectorStoreL2 rejects missing/invalid tokens."""
    priv, pub = agent_keys
    agent_id = "agent_1"

    item_mem = ItemMemory(dim=128)
    encoder = HDCEncoder(item_mem)
    db_file = tmp_path / "hdc.db"

    store = HDCVectorStoreL2(encoder, item_mem, db_path=db_file)
    conn = store._get_conn()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, name TEXT, agent_type TEXT, reputation_score REAL, public_key TEXT, tenant_id TEXT, is_active INTEGER DEFAULT 1)"
    )
    conn.execute(
        "INSERT INTO agents (id, name, agent_type, reputation_score, public_key, tenant_id) VALUES (?, ?, ?, 1.0, ?, 'default')",
        (agent_id, "Agent", "ai", pub),
    )
    conn.commit()

    # Missing token
    fact_missing = CortexFactModel(
        tenant_id="default",
        project_id="default",
        content="HDC Fact",
        embedding=[0.1] * 128,
        metadata={},
    )
    with pytest.raises(TaintValidationError):
        await store.memorize(fact_missing)

    # Valid token
    valid_token = generate_secure_taint_token(agent_id, "session_1", "HDC Fact", priv)
    fact_valid = CortexFactModel(
        tenant_id="default",
        project_id="default",
        content="HDC Fact",
        embedding=[0.1] * 128,
        metadata={"cortex_taint": valid_token},
    )
    # Should succeed
    await store.memorize(fact_valid)
    await store.close()


@pytest.mark.asyncio
async def test_write_trait_taint_rejection(clean_db, agent_keys):
    """Verifies WriteTrait rejects missing/invalid tokens."""
    priv, pub = agent_keys
    agent_id = "agent_1"

    clean_db.execute(
        "INSERT INTO agents (id, name, agent_type, reputation_score, public_key, tenant_id) VALUES (?, ?, ?, 1.0, ?, 'default')",
        (agent_id, "Agent", "ai", pub),
    )
    clean_db.commit()

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
        embedding=[0.1] * 384,
        metadata={},
    )
    with pytest.raises(TaintValidationError):
        await writer.memorize(fact_missing)

    # Valid token
    valid_token = generate_secure_taint_token(agent_id, "session_1", "WriteTrait Fact", priv)
    fact_valid = CortexFactModel(
        tenant_id="def",
        project_id="proj",
        content="WriteTrait Fact",
        embedding=[0.1] * 384,
        metadata={"cortex_taint": valid_token},
    )
    # Should succeed
    await writer.memorize(fact_valid)


@pytest.mark.asyncio
async def test_expired_timestamp_rejection(agent_keys):
    """Verifies tokens older than 5 minutes are rejected."""
    priv, pub = agent_keys
    agent_id = "agent_1"

    async with aiosqlite.connect(":memory:") as aio_conn:
        await setup_aio_db(aio_conn, agent_id, pub)

        # Force an expired timestamp (6 minutes ago)
        expired_time = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()
        content = "Expired Content"
        canonical_content = canonicalize_content(content)
        content_hash = hashlib.sha3_256(canonical_content.encode("utf-8")).hexdigest()

        # Sign payload manually
        payload = f"agent_id={agent_id}&session_id=s1&timestamp={expired_time}&nonce=n1&content_hash={content_hash}"
        priv_bytes = base64.b64decode(priv)
        priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        sig = base64.b64encode(priv_key.sign(payload.encode("utf-8"))).decode("ascii")

        expired_token = f"taint:{agent_id}:s1:{expired_time}:n1:{sig}"

        with pytest.raises(TaintValidationError):
            await insert_fact_record(
                aio_conn,
                tenant_id="default",
                project="default",
                content=content,
                fact_type="general",
                tags=None,
                confidence="C5",
                ts=None,
                source=None,
                meta={"cortex_taint": expired_token},
                tx_id=None,
            )


@pytest.mark.asyncio
async def test_verification_oracle_invariants(agent_keys):
    """Verifies that verify_c5_state_machine formally checks invariants."""
    priv, pub = agent_keys
    agent_id = "agent_1"

    async with aiosqlite.connect(":memory:") as aio_conn:
        await setup_aio_db(aio_conn, agent_id, pub)

        # 1. State machine should pass with empty tables
        assert await verify_c5_state_machine(aio_conn) is True

        # 2. Add some causal edges (clean DAG)
        await aio_conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, edge_type, project, tenant_id) VALUES (1, NULL, 'trigger', 'p1', 'default')"
        )
        await aio_conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, edge_type, project, tenant_id) VALUES (2, 1, 'trigger', 'p1', 'default')"
        )
        await aio_conn.commit()
        assert await verify_c5_state_machine(aio_conn) is True

        # 3. Add a cycle to causal_edges (violates Inv-3)
        await aio_conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id, edge_type, project, tenant_id) VALUES (1, 2, 'trigger', 'p1', 'default')"
        )
        await aio_conn.commit()
        with pytest.raises(InvariantViolationError):
            await verify_c5_state_machine(aio_conn)

        # Remove cycle to fix it
        await aio_conn.execute("DELETE FROM causal_edges WHERE fact_id = 1 AND parent_id = 2")
        await aio_conn.commit()
        assert await verify_c5_state_machine(aio_conn) is True

        # 4. Add approved auth override without signature (violates Inv-4)
        await aio_conn.execute(
            "INSERT INTO auth_requests (id, hypothesis, state_payload, status) VALUES ('req_1', 'hyp', '{}', 'APPROVED')"
        )
        await aio_conn.commit()
        with pytest.raises(InvariantViolationError):
            await verify_c5_state_machine(aio_conn)
