import logging
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

import cortex.api.state as api_state
import cortex.auth
from cortex import config
from cortex.api.core import app
from cortex.auth import AuthManager
from cortex.database.core import connect as db_connect
from cortex.database.pool import CortexConnectionPool
from cortex.engine import CortexEngine
from cortex.engine_async import AsyncCortexEngine
from cortex.timing import TimingTracker

logger = logging.getLogger(__name__)


@pytest.fixture
async def client():
    # Setup unique test DB
    test_db = f"test_security_{uuid.uuid4().hex[:8]}.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize engine and auth with test DB
    test_engine = CortexEngine(test_db)
    await test_engine.init_db()

    test_auth_manager = AuthManager(test_db)
    await test_auth_manager.initialize()

    # Create connection pool and async engine for the API to use
    test_pool = CortexConnectionPool(test_db, read_only=False)
    await test_pool.initialize()
    test_async_engine = AsyncCortexEngine(test_pool, test_db)

    # Timing tracker
    timing_conn = db_connect(test_db)
    test_tracker = TimingTracker(timing_conn)

    # Save old globals and config
    old_engine = api_state.engine
    old_auth = api_state.auth_manager
    old_cortex_auth = cortex.auth.manager._auth_manager
    old_db_path = config.DB_PATH

    # Backup app.state
    backup_state = {
        "pool": getattr(app.state, "pool", None),
        "async_engine": getattr(app.state, "async_engine", None),
        "engine": getattr(app.state, "engine", None),
        "auth_manager": getattr(app.state, "auth_manager", None),
        "tracker": getattr(app.state, "tracker", None),
    }

    # Patch app.state
    app.state.pool = test_pool
    app.state.async_engine = test_async_engine
    app.state.engine = test_engine
    app.state.auth_manager = test_auth_manager
    app.state.tracker = test_tracker

    # Re-patch globals
    api_state.engine = test_engine
    api_state.auth_manager = test_auth_manager
    cortex.auth.manager._auth_manager = test_auth_manager
    config.DB_PATH = test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Cleanup in reverse order
    await test_async_engine._pool.close()
    await test_engine.close()
    timing_conn.close()

    # Restore app.state
    for k, v in backup_state.items():
        setattr(app.state, k, v)

    # Restore Globals and config
    api_state.engine = old_engine
    api_state.auth_manager = old_auth
    cortex.auth.manager._auth_manager = old_cortex_auth
    config.DB_PATH = old_db_path

    # Clean up test DB files
    for ext in ["", "-wal", "-shm"]:
        target = test_db + ext
        if os.path.exists(target):
            try:
                os.unlink(target)
            except OSError:
                pass


@pytest.mark.asyncio
async def test_consensus_tenant_isolation(client):
    """Verify that tenants cannot vote or read votes for each other's facts."""
    am = api_state.auth_manager
    raw_key1, _ = await am.create_key("T1", tenant_id="tenant1", permissions=["read", "write"])
    raw_key2, _ = await am.create_key("T2", tenant_id="tenant2", permissions=["read", "write"])

    # 1. Tenant 1 stores a fact
    resp = await client.post(
        "/v1/facts",
        json={"project": "tenant1", "content": "Fact from T1 is long enough now", "source": "api"},
        headers={"Authorization": f"Bearer {raw_key1}"},
    )
    assert resp.status_code == 200, f"Setup failed: {resp.text}"
    fact_id = resp.json()["fact_id"]

    # 2. Tenant 2 tries to vote on Tenant 1's fact (Should fail 403)
    resp = await client.post(
        f"/v1/facts/{fact_id}/vote",
        json={"value": 1},
        headers={"Authorization": f"Bearer {raw_key2}"},
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]

    # 3. Tenant 2 tries to read votes for Tenant 1's fact (Should fail 403)
    resp = await client.get(
        f"/v1/facts/{fact_id}/votes", headers={"Authorization": f"Bearer {raw_key2}"}
    )
    assert resp.status_code == 403

    # 4. Tenant 1 votes on their own fact (Should succeed)
    resp = await client.post(
        f"/v1/facts/{fact_id}/vote",
        json={"value": 1},
        headers={"Authorization": f"Bearer {raw_key1}"},
    )
    assert resp.status_code == 200
    assert resp.json()["new_consensus_score"] > 1.0


@pytest.mark.asyncio
async def test_vote_validation(client):
    """Verify pydantic validation and core auth logic."""
    am = api_state.auth_manager
    raw_key1, _ = await am.create_key("T1", tenant_id="tenant1", permissions=["read", "write"])

    resp = await client.post(
        "/v1/facts",
        json={"project": "tenant1", "content": "Fact from T1 is long enough now", "source": "api"},
        headers={"Authorization": f"Bearer {raw_key1}"},
    )
    assert resp.status_code == 200
    fact_id = resp.json()["fact_id"]

    # Test invalid vote value (Pydantic validation layer check)
    resp = await client.post(
        f"/v1/facts/{fact_id}/vote",
        json={"agent": "tester", "value": 5},
        headers={"Authorization": f"Bearer {raw_key1}"},
    )
    # The API might return 422 if it hits Pydantic, or 400 if it passes to engine
    assert resp.status_code in (400, 422)
