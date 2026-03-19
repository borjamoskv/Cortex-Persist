from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import cortex.api.state as api_state
import cortex.auth.manager as auth_manager_module
from cortex.auth.manager import AuthManager
from cortex.database.pool import CortexConnectionPool
from cortex.engine import CortexEngine
from cortex.engine_async import AsyncCortexEngine
from cortex.routes import facts as facts_router


@pytest.fixture
def tenant_client(tmp_path) -> Iterator[tuple[TestClient, str, str]]:
    db_path = tmp_path / "tenant_isolation.db"

    # Same boot path as API lifespan: schema/init -> auth -> pool -> async engine.
    engine = CortexEngine(str(db_path), auto_embed=False)
    asyncio.run(engine.init_db())

    auth_manager = AuthManager(str(db_path))
    auth_manager.initialize_sync()

    pool = CortexConnectionPool(str(db_path), read_only=False)
    asyncio.run(pool.initialize())
    async_engine = AsyncCortexEngine(pool, str(db_path))

    token_a, _ = auth_manager.create_key_sync(
        "tenant-a-admin",
        tenant_id="tenant_a",
        permissions=["read", "write", "admin"],
    )
    token_b, _ = auth_manager.create_key_sync(
        "tenant-b-admin",
        tenant_id="tenant_b",
        permissions=["read", "write", "admin"],
    )

    previous_api_manager = api_state.auth_manager
    previous_global_manager = auth_manager_module._auth_manager
    api_state.auth_manager = auth_manager
    auth_manager_module._auth_manager = auth_manager

    app = FastAPI()
    app.state.async_engine = async_engine
    app.state.engine = engine
    app.include_router(facts_router.router)
    client = TestClient(app)

    try:
        yield client, token_a, token_b
    finally:
        client.close()

        async def _cleanup() -> None:
            await pool.close()
            await engine.close()
            await auth_manager.close()

        asyncio.run(_cleanup())
        api_state.auth_manager = previous_api_manager
        auth_manager_module._auth_manager = previous_global_manager


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _store_fact(client: TestClient, token: str, content: str, project: str = "shared") -> int:
    response = client.post(
        "/v1/facts",
        headers=_auth_header(token),
        json={
            "project": project,
            "content": content,
            "fact_type": "knowledge",
            "tags": ["isolation"],
            "source": "test:e2e",
            "meta": {"suite": "tenant_isolation"},
        },
    )
    assert response.status_code == 200, response.text
    return int(response.json()["fact_id"])


def test_tenants_cannot_read_each_others_facts(tenant_client) -> None:
    client, token_a, token_b = tenant_client
    fact_a = _store_fact(client, token_a, "private note tenant a")
    fact_b = _store_fact(client, token_b, "private note tenant b")

    list_a = client.get("/v1/facts", headers=_auth_header(token_a), params={"limit": 100})
    assert list_a.status_code == 200
    contents_a = {item["content"] for item in list_a.json()}
    assert "private note tenant a" in contents_a
    assert "private note tenant b" not in contents_a

    list_b = client.get("/v1/facts", headers=_auth_header(token_b), params={"limit": 100})
    assert list_b.status_code == 200
    contents_b = {item["content"] for item in list_b.json()}
    assert "private note tenant b" in contents_b
    assert "private note tenant a" not in contents_b

    # Direct cross-tenant access by fact_id must be blocked.
    assert client.get(f"/v1/facts/{fact_b}", headers=_auth_header(token_a)).status_code == 404
    assert client.get(f"/v1/facts/{fact_a}", headers=_auth_header(token_b)).status_code == 404


def test_tenants_cannot_vote_or_list_votes_cross_tenant(tenant_client) -> None:
    client, token_a, token_b = tenant_client
    _ = _store_fact(client, token_a, "vote payload tenant a")
    fact_b = _store_fact(client, token_b, "vote payload tenant b")

    # Cross-tenant vote and vote listing must be denied as not-found (opaque isolation).
    cross_vote = client.post(
        f"/v1/facts/{fact_b}/vote",
        headers=_auth_header(token_a),
        json={"value": 1},
    )
    assert cross_vote.status_code == 404

    cross_votes = client.get(f"/v1/facts/{fact_b}/votes", headers=_auth_header(token_a))
    assert cross_votes.status_code == 404


def test_causal_chain_is_tenant_scoped(tenant_client) -> None:
    client, token_a, token_b = tenant_client
    fact_b = _store_fact(client, token_b, "chain payload tenant b")

    # Chain endpoint must never leak foreign-tenant facts.
    chain = client.get(
        f"/v1/facts/{fact_b}/chain",
        headers=_auth_header(token_a),
        params={"direction": "down", "max_depth": 10},
    )
    assert chain.status_code == 200
    assert chain.json() == []
