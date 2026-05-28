from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.consensus.manager import ConsensusManager
from cortex.database.pool import CortexConnectionPool
from cortex.database.schema import get_all_schema
from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.routes import facts as facts_router


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


@pytest.fixture
async def engine(tmp_path):
    db_path = str(tmp_path / "consensus.db")
    pool = CortexConnectionPool(db_path, read_only=False)
    await pool.initialize()

    async with pool.acquire() as conn:
        for sql in get_all_schema():
            if "USING vec0" in sql:
                continue
            await conn.executescript(sql)
        await conn.commit()

    engine = AsyncCortexEngine(pool, db_path)
    try:
        yield engine
    finally:
        await pool.close()


async def _seed_fact_and_agent(
    engine: AsyncCortexEngine,
    *,
    fact_tenant: str,
    agent_tenant: str,
    fact_id: int = 1,
    agent_id: str = "agent-a",
) -> None:
    async with engine.session() as conn:
        await conn.execute(
            "INSERT INTO facts "
            "(id, tenant_id, project, content, fact_type, confidence, valid_from, tags, "
            "source, metadata, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fact_id,
                fact_tenant,
                "project-a",
                "content",
                "knowledge",
                "C3",
                "2026-01-01",
                "[]",
                "test",
                "{}",
                "2026-01-01",
                "2026-01-01",
            ),
        )
        await conn.execute(
            "INSERT INTO agents "
            "(id, public_key, name, agent_type, tenant_id, is_active, reputation_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (agent_id, "pub", "Agent A", "ai", agent_tenant, 1, 0.5),
        )
        await conn.commit()


@pytest.mark.asyncio
async def test_consensus_vote_v2_resolves_fact_tenant_when_unspecified(engine) -> None:
    await _seed_fact_and_agent(engine, fact_tenant="tenant-a", agent_tenant="tenant-a")

    manager = ConsensusManager(engine)
    score = await manager.vote_v2(fact_id=1, agent_id="agent-a", value=1)

    async with engine.session() as conn:
        row = await (
            await conn.execute(
                "SELECT tenant_id, vote FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",
                (1, "agent-a"),
            )
        ).fetchone()

    assert isinstance(score, float)
    assert row == ("tenant-a", 1)


@pytest.mark.asyncio
async def test_consensus_vote_v2_rejects_cross_tenant_agent(engine) -> None:
    await _seed_fact_and_agent(engine, fact_tenant="tenant-a", agent_tenant="tenant-b")

    manager = ConsensusManager(engine)
    with pytest.raises(ValueError, match="not found for tenant tenant-a"):
        await manager.vote_v2(fact_id=1, agent_id="agent-a", value=1, tenant_id="tenant-a")

    async with engine.session() as conn:
        row = await (
            await conn.execute("SELECT COUNT(*) FROM consensus_votes_v2 WHERE fact_id = ?", (1,))
        ).fetchone()

    assert row[0] == 0


def test_vote_v2_route_passes_agent_id_and_tenant_keyword() -> None:
    observed: dict[str, Any] = {}

    class FakeEngine:
        async def get_fact(self, fact_id: int, tenant_id: str = "default"):
            assert tenant_id == "tenant-a"
            return {"id": fact_id, "confidence": "verified"}

        async def vote_v2(self, **kwargs):
            observed.update(kwargs)
            return 1.8

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}/vote-v2",
        "POST",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}/vote-v2", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-a",
        permissions=["write"],
        key_name="api-key",
    )
    app.dependency_overrides[get_async_engine] = lambda: FakeEngine()

    with TestClient(app) as client:
        response = client.post("/v1/facts/1/vote-v2", json={"agent_id": "agent-a", "vote": 1})

    assert response.status_code == 200
    assert observed == {"fact_id": 1, "agent_id": "agent-a", "value": 1, "tenant_id": "tenant-a"}
