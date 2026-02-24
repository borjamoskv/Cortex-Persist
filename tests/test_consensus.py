import os
import unittest.mock as mock

import pytest
from httpx import ASGITransport, AsyncClient

# Integration test for the Consensus System


@pytest.fixture(scope="function")
async def client(monkeypatch):
    test_db = "test_consensus_final.db"
    # Clean up any leftover db files
    for suffix in ("", "-wal", "-shm"):
        path = test_db + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # Patch environment
    monkeypatch.setenv("CORTEX_DB", test_db)

    import cortex.config
    from cortex.database.pool import CortexConnectionPool
    from cortex.engine_async import AsyncCortexEngine
    from cortex.engine import CortexEngine
    from cortex.database.core import connect as db_connect
    from cortex.timing import TimingTracker

    monkeypatch.setattr(cortex.config, "DB_PATH", test_db)

    # Now import app and state
    import cortex.auth
    import cortex.api.state as api_state
    from cortex.api.core import app

    # Set up some test state
    monkeypatch.setattr(cortex.auth, "_auth_manager", None)

    # Mock Embedder to avoid model download/hang
    with mock.patch("cortex.embeddings.LocalEmbedder") as mock_embedder:
        instance = mock_embedder.return_value
        instance.embed.return_value = [0.1] * 384
        instance.embed_batch.return_value = [[0.1] * 384]
        instance.dimension = 384

        # Initialize engines
        test_engine = CortexEngine(test_db)
        await test_engine.init_db()

        test_pool = CortexConnectionPool(test_db, read_only=False)
        await test_pool.initialize()
        test_async_engine = AsyncCortexEngine(test_pool, test_db)

        timing_conn = db_connect(test_db)
        test_tracker = TimingTracker(timing_conn)

        # Re-initialize auth manager for the new DB
        from cortex.auth import AuthManager
        api_state.auth_manager = AuthManager(test_db)
        await api_state.auth_manager.initialize()

        # Patch app.state
        app.state.pool = test_pool
        app.state.async_engine = test_async_engine
        app.state.engine = test_engine
        app.state.auth_manager = api_state.auth_manager
        app.state.tracker = test_tracker

        # Re-patch globals
        old_engine = api_state.engine
        api_state.engine = test_engine

        raw_key, _ = await api_state.auth_manager.create_key(
            "api_agent",
            tenant_id="test_proj",
            permissions=["read", "write", "admin"],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.headers.update({"Authorization": f"Bearer {raw_key}"})
            yield c

        # Restore globals
        api_state.engine = old_engine

        # Cleanup
        await test_pool.close()
        await test_engine.close()
        timing_conn.close()


@pytest.mark.asyncio
async def test_consensus_flow(client):
    """Test standard consensus flow (upvote/downvote)."""
    # 1. Register agent
    resp = await client.post("/v1/agents", json={"name": "test-agent", "agent_type": "ai"})
    assert resp.status_code == 200
    resp.json()["agent_id"]  # verify key exists

    # 2. Store fact
    resp = await client.post(
        "/v1/facts",
        json={
            "project": "test_proj",
            "content": "The Earth is round and beautiful",
            "source": "cli",
        },
    )
    if resp.status_code != 200:
        print(f"DEBUG 422 validation: {resp.text}")
    assert resp.status_code == 200
    fact_id = resp.json()["fact_id"]

    # 3. Upvote
    resp = await client.post(f"/v1/facts/{fact_id}/vote", json={"value": 1})
    if resp.status_code != 200:
        print(f"DEBUG VOTE1: {resp.text}")
    assert resp.status_code == 200
    assert resp.json()["new_consensus_score"] > 1.0

    # 4. Downvote
    resp = await client.post(f"/v1/facts/{fact_id}/vote", json={"value": -1})
    if resp.status_code != 200:
        print(f"DEBUG VOTE2: {resp.text}")
    assert resp.status_code == 200
    assert resp.json()["new_consensus_score"] < 1.0


@pytest.mark.asyncio
async def test_recall_ordering(client):
    """Test standard recall ordering (score + recency)."""
    # Store via API to use the initialized async connection
    resp_a = await client.post(
        "/v1/facts",
        json={"project": "test_proj", "content": "Fact A: This is a long content", "source": "cli"},
    )
    assert resp_a.status_code == 200
    resp_b = await client.post(
        "/v1/facts",
        json={"project": "test_proj", "content": "Fact B: This is a long content", "source": "cli"},
    )
    assert resp_b.status_code == 200
    resp_c = await client.post(
        "/v1/facts",
        json={"project": "test_proj", "content": "Fact C: This is a long content", "source": "cli"},
    )
    assert resp_c.status_code == 200
    fid_c = resp_c.json()["fact_id"]

    # 2. Add some votes to Fact C (Upvote)
    await client.post(f"/v1/facts/{fid_c}/vote", json={"value": 1})

    # 3. Recall and check order (Fact C should be first)
    resp = await client.get("/v1/projects/test_proj/facts")
    facts = resp.json()
    assert facts[0]["content"] == "Fact C: This is a long content"


@pytest.mark.asyncio
async def test_rwc_flow(client):
    """Test Reputation-Weighted Consensus flow."""
    import cortex.api.state as api_state

    engine = api_state.engine

    # 1. Register 2 agents
    resp1 = await client.post("/v1/agents", json={"name": "whale", "agent_type": "ai"})
    agent_whale = resp1.json()["agent_id"]

    resp2 = await client.post("/v1/agents", json={"name": "shrimp", "agent_type": "ai"})
    agent_shrimp = resp2.json()["agent_id"]

    # 2. Boost reputation in DB
    conn = await engine.get_conn()
    await conn.execute("UPDATE agents SET reputation_score = 10.0 WHERE id = ?", (agent_whale,))
    await conn.execute("UPDATE agents SET reputation_score = 1.0 WHERE id = ?", (agent_shrimp,))
    await conn.commit()

    # 3. Store a fact
    fid = await engine.store("test_proj", "Reputation Test Fact Content Long", source="cli")

    # 4. Shrimp downvotes (-1), Whale upvotes (+1)
    await client.post(f"/v1/facts/{fid}/vote-v2", json={"agent_id": agent_shrimp, "vote": -1})
    await client.post(f"/v1/facts/{fid}/vote-v2", json={"agent_id": agent_whale, "vote": 1})

    # 5. Check score (should be > 1.0 because whale has more weight)
    resp_recall = await client.get("/v1/projects/test_proj/facts")
    fact = next(f for f in resp_recall.json() if f["id"] == fid)

    assert fact["consensus_score"] > 1.0
    assert fact["confidence"] == "verified"
