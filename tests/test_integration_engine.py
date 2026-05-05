import asyncio
import hashlib

import pytest

from cortex.consensus.manager import ConsensusManager
from cortex.consensus.vote_ledger import ImmutableVoteLedger
from cortex.database.schema import get_all_schema
from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.ledger import ImmutableLedger


@pytest.fixture
async def engine(tmp_path):
    from cortex.database.pool import CortexConnectionPool

    # Setup temporary DB file
    db_path = str(tmp_path / "test_cortex.db")

    pool = CortexConnectionPool(db_path, read_only=False)
    await pool.initialize()

    # Load schema
    async with pool.acquire() as conn:
        for sql in get_all_schema():
            if "USING vec0" in sql:
                continue
            await conn.executescript(sql)
        await conn.commit()

    engine = AsyncCortexEngine(pool, db_path)
    yield engine
    await pool.close()


@pytest.mark.asyncio
async def test_connection_pool_stability(engine):
    """Verify that concurrent operations don't leak connections or timeout."""
    # Insert required fact and agents for foreign key constraints
    async with engine.session() as conn:
        await conn.execute(
            "INSERT INTO facts (id, content, hash, project) VALUES (?, ?, ?, ?)",
            (1, "Test Fact", hashlib.sha256(b"Test Fact").hexdigest(), "test_proj"),
        )
        for i in range(100):
            await conn.execute(
                "INSERT INTO agents (id, public_key, name, is_active, reputation_score) VALUES (?, ?, ?, ?, ?)",
                (f"agent_{i}", f"pub_{i}", f"Agent {i}", 1, 0.5),
            )
        await conn.commit()

    manager = ConsensusManager(engine)

    # Simulate 100 concurrent votes
    tasks = []
    for i in range(100):
        tasks.append(manager.vote_v2(fact_id=1, agent_id=f"agent_{i}", value=1))

    # This should complete without "Too many open connections" or pool timeouts
    scores = await asyncio.gather(*tasks)
    assert len(scores) == 100
    assert all(isinstance(s, (int, float)) for s in scores)


@pytest.mark.asyncio
async def test_multi_tenant_isolation(engine):
    """Verify that tenant_id is enforced and isolated."""
    # Note: This test assumes schema for consensus_votes was updated with tenant_id
    # We use a custom query to verify since ConsensusManager doesn't expose tenant filtering yet

    async with engine.session() as conn:
        # Insert required fact
        await conn.execute(
            "INSERT INTO facts (id, content, project) VALUES (10, 'Tenant Fact', 'test_proj')"
        )

        # Seed agents for isolation test
        await conn.execute(
            "INSERT INTO agents (id, public_key, name, is_active, reputation_score) VALUES (?, ?, ?, ?, ?)",
            ("agent_A", "pub_A", "Agent A", 1, 0.5),
        )
        await conn.execute(
            "INSERT INTO agents (id, public_key, name, is_active, reputation_score) VALUES (?, ?, ?, ?, ?)",
            ("agent_B", "pub_B", "Agent B", 1, 0.5),
        )

        # Add a vote for tenant A
        await conn.execute(
            """INSERT INTO consensus_votes_v2 
               (fact_id, agent_id, vote, tenant_id, vote_weight, agent_rep_at_vote) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (10, "agent_A", 1, "tenant_A", 1.0, 0.5),
        )
        # Add a vote for tenant B
        await conn.execute(
            """INSERT INTO consensus_votes_v2 
               (fact_id, agent_id, vote, tenant_id, vote_weight, agent_rep_at_vote) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (10, "agent_B", -1, "tenant_B", 1.0, 0.5),
        )
        await conn.commit()

        # Verify isolation via raw SQL
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM consensus_votes_v2 WHERE tenant_id = ?", ("tenant_A",)
        )
        row_a = await cursor.fetchone()
        assert row_a[0] == 1

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM consensus_votes_v2 WHERE tenant_id = ?", ("tenant_B",)
        )
        row_b = await cursor.fetchone()
        assert row_b[0] == 1


@pytest.mark.asyncio
async def test_vote_v2_binds_votes_and_transactions_to_fact_tenant(engine):
    """Votes should inherit the fact tenant and keep the public agent name clean."""
    async with engine.session() as conn:
        await conn.execute(
            "INSERT INTO facts (id, tenant_id, content, hash, project) VALUES (?, ?, ?, ?, ?)",
            (
                42,
                "tenant_A",
                "Tenant-scoped fact",
                hashlib.sha256(b"Tenant-scoped fact").hexdigest(),
                "test_proj",
            ),
        )
        await conn.commit()

    manager = ConsensusManager(engine)
    score = await manager.vote_v2(fact_id=42, agent_id="tenant_A:agent_A", value=1)
    assert isinstance(score, float)

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT agent_id, tenant_id FROM consensus_votes_v2 WHERE fact_id = ?",
            (42,),
        )
        vote_row = await cursor.fetchone()
        assert vote_row == ("tenant_A:agent_A", "tenant_A")

        cursor = await conn.execute(
            "SELECT name, tenant_id FROM agents WHERE id = ?",
            ("tenant_A:agent_A",),
        )
        agent_row = await cursor.fetchone()
        assert agent_row == ("agent_A", "tenant_A")

        cursor = await conn.execute(
            "SELECT tenant_id, action FROM transactions WHERE project = ? ORDER BY id DESC LIMIT 1",
            ("consensus",),
        )
        tx_row = await cursor.fetchone()
        assert tx_row == ("tenant_A", "vote_v2")

        cursor = await conn.execute(
            "SELECT fact_hash FROM vote_ledger WHERE fact_id = ? AND tenant_id = ?",
            (42, "tenant_A"),
        )
        ledger_row = await cursor.fetchone()
        assert ledger_row == (hashlib.sha256(b"Tenant-scoped fact").hexdigest(),)

    ledger_report = await engine.verify_vote_ledger("tenant_A")
    assert ledger_report["valid"] is True
    assert ledger_report["votes_checked"] == 1

    async with engine.session() as conn:
        ledger = ImmutableVoteLedger(conn)
        root = await ledger.checkpoint_merkle_root("tenant_A")
        merkle_report = await ledger.verify_merkle_roots("tenant_A")
        assert root
        assert merkle_report[-1]["valid"] is True

    votes = await engine.get_votes(42, tenant_id="tenant_A")
    assert len(votes) == 1
    assert votes[0]["agent"] == "agent_A"
    assert votes[0]["vote"] == 1

    async with engine.session() as conn:
        await conn.execute(
            "UPDATE facts SET hash = ? WHERE id = ? AND tenant_id = ?",
            ("tampered", 42, "tenant_A"),
        )
        await conn.commit()

    tamper_report = await engine.verify_vote_ledger("tenant_A")
    assert tamper_report["valid"] is False
    assert any(v["type"] == "fact_hash_mismatch" for v in tamper_report["violations"])


@pytest.mark.asyncio
async def test_vote_ledger_verification_checks_merkle_checkpoints(engine):
    async with engine.session() as conn:
        await conn.execute(
            "INSERT INTO facts (id, tenant_id, content, hash, project) VALUES (?, ?, ?, ?, ?)",
            (
                44,
                "tenant_A",
                "Merkle-bound vote fact",
                hashlib.sha256(b"Merkle-bound vote fact").hexdigest(),
                "test_proj",
            ),
        )
        await conn.commit()

    manager = ConsensusManager(engine)
    await manager.vote_v2(fact_id=44, agent_id="tenant_A:agent_A", value=1)

    from cortex.consensus.vote_ledger import ImmutableVoteLedger

    async with engine.session() as conn:
        vote_ledger = ImmutableVoteLedger(conn)
        checkpoint_root = await vote_ledger.checkpoint_merkle_root("tenant_A")
        assert checkpoint_root

        cursor = await conn.execute(
            """
            SELECT id, tenant_id, fact_id, fact_hash, agent_id, vote_weight,
                   prev_hash, timestamp, signature
            FROM vote_ledger
            WHERE fact_id = ? AND tenant_id = ?
            """,
            (44, "tenant_A"),
        )
        row = await cursor.fetchone()
        new_hash = vote_ledger._compute_hash(
            tenant_id=row[1],
            prev_hash=row[6],
            fact_id=row[2],
            fact_hash=row[3],
            agent_id=row[4],
            vote=-1,
            vote_weight=row[5],
            timestamp=row[7],
            signature=row[8],
        )
        await conn.execute(
            "UPDATE vote_ledger SET vote = ?, hash = ? WHERE id = ?",
            (-1, new_hash, row[0]),
        )
        await conn.commit()

    report = await engine.verify_vote_ledger("tenant_A")

    assert report["valid"] is False
    assert report["checkpoints_checked"] == 1
    assert any(v["type"] == "vote_merkle_mismatch" for v in report["violations"])


@pytest.mark.asyncio
async def test_vote_v2_noop_unvote_does_not_create_agent(engine):
    async with engine.session() as conn:
        await conn.execute(
            "INSERT INTO facts (id, tenant_id, content, hash, project) VALUES (?, ?, ?, ?, ?)",
            (
                43,
                "tenant_A",
                "Tenant-scoped fact",
                hashlib.sha256(b"Tenant-scoped fact").hexdigest(),
                "test_proj",
            ),
        )
        await conn.commit()

    manager = ConsensusManager(engine)
    score = await manager.vote_v2(fact_id=43, agent_id="ghost-agent", value=0)
    assert isinstance(score, float)

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM agents WHERE id = ? AND tenant_id = ?",
            ("ghost-agent", "tenant_A"),
        )
        agent_count = await cursor.fetchone()
        assert agent_count[0] == 0

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE action = ? AND tenant_id = ?",
            ("unvote_v2", "tenant_A"),
        )
        tx_count = await cursor.fetchone()
        assert tx_count[0] == 0


@pytest.mark.asyncio
async def test_engine_exposes_trust_registry_wrapper(engine):
    """The composite engine should expose the trust registry used by the trust routes."""
    registry = engine.get_trust_registry()
    assert registry is engine.get_trust_registry()
    profile = registry.get_profile("agent-x")
    assert profile.agent_id == "agent-x"


@pytest.mark.asyncio
async def test_engine_exposes_agent_registry_wrappers(engine):
    """Agent routes should be backed by live engine methods, not orphaned mixins."""
    agent_id = await engine.register_agent(
        name="agent-alpha",
        agent_type="ai",
        public_key="pub-alpha",
        tenant_id="tenant_agents",
        moltbook_sync=False,
    )
    assert isinstance(agent_id, str)

    agent = await engine.get_agent(agent_id, tenant_id="tenant_agents")
    assert agent is not None
    assert agent["name"] == "agent-alpha"
    assert agent["agent_type"] == "ai"

    agents = await engine.list_agents(tenant_id="tenant_agents")
    assert [a["id"] for a in agents] == [agent_id]


@pytest.mark.asyncio
async def test_transaction_checkpoints_and_verification_are_tenant_scoped(engine):
    """Merkle checkpoints should only cover transactions from the requested tenant."""
    async with engine.session() as conn:
        await engine._log_transaction(
            conn,
            "tenant_proj",
            "store",
            {"fact_id": 1},
            tenant_id="tenant_A",
        )
        await engine._log_transaction(
            conn,
            "tenant_proj",
            "store",
            {"fact_id": 2},
            tenant_id="tenant_B",
        )
        await conn.commit()

    engine._ledger = ImmutableLedger(engine._pool)
    engine._ledger._config.CHECKPOINT_MIN = 1
    engine._ledger._config.CHECKPOINT_MAX = 1

    checkpoint_a = await engine.create_checkpoint(tenant_id="tenant_A")
    checkpoint_b = await engine.create_checkpoint(tenant_id="tenant_B")
    assert checkpoint_a is not None
    assert checkpoint_b is not None

    report_a = await engine.verify_ledger(tenant_id="tenant_A")
    report_b = await engine.verify_ledger(tenant_id="tenant_B")
    full_report = await engine.verify_ledger()

    assert report_a["valid"] is True
    assert report_b["valid"] is True
    assert full_report["valid"] is True
    assert report_a["roots_checked"] == 1
    assert report_b["roots_checked"] == 1

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT tenant_id, COUNT(*) FROM merkle_roots GROUP BY tenant_id ORDER BY tenant_id"
        )
        rows = await cursor.fetchall()
        assert rows == [("tenant_A", 1), ("tenant_B", 1)]


@pytest.mark.asyncio
async def test_taint_propagation_crypto_safety(engine):
    """Verify that taint propagation doesn't clobber encrypted-looking metadata."""
    async with engine.session() as conn:
        # 1. Insert fact 500
        encrypted_blob = "Ω-ENCRYPTED-CRYPTO-STUFF-Ω"
        await conn.execute(
            "INSERT INTO facts (id, content, project, confidence, metadata) VALUES (?, ?, ?, ?, ?)",
            (500, "Secret Fact", "project_x", "C5", encrypted_blob),
        )

        # 2. Insert fact 501 first (so edge can reference it)
        await conn.execute(
            "INSERT INTO facts (id, content, project, confidence, metadata) VALUES (?, ?, ?, ?, ?)",
            (501, "Derived Fact", "project_x", "C5", "{}"),
        )

        # 3. Add a causal edge
        await conn.execute(
            "INSERT INTO causal_edges (fact_id, parent_id) VALUES (?, ?)", (501, 500)
        )
        await conn.commit()

    # 3. Propagate taint from fact 500
    from cortex.engine.causality import AsyncCausalGraph

    async with engine.session() as conn:
        graph = AsyncCausalGraph(conn)
        await graph.propagate_taint(fact_id=500, floor_to_c1=True)

    # 4. Verify that metadata of fact 500 was NOT clobbered
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT confidence, metadata FROM facts WHERE id = ?", (500,))
        row = await cursor.fetchone()
        assert row[0] == "C1"  # Confidence SHOULD be downgraded
        assert row[1] == encrypted_blob  # Metadata SHOULD remain intact
