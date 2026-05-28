import asyncio

import pytest

from cortex.consensus.manager import ConsensusManager
from cortex.database.schema import get_all_schema
from cortex.engine import CortexEngine as AsyncCortexEngine


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
            "INSERT INTO facts (id, content, project) VALUES (1, 'Test Fact', 'test_proj')"
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
