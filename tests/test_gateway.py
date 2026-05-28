from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.gateway import GatewayIntent, GatewayRequest, GatewayRouter


@pytest.mark.asyncio
async def test_gateway_router_store_success():
    """Verify that GatewayRouter accurately routes STORE intent."""
    mock_engine = AsyncMock()
    mock_engine.store.return_value = "fact_123"

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(
        intent=GatewayIntent.STORE,
        project="test_proj",
        payload={"content": "test content", "type": "knowledge"},
    )

    resp = await router.handle(req)

    assert resp.ok is True
    assert resp.data["fact_id"] == "fact_123"
    mock_engine.store.assert_called_once_with(
        project="test_proj",
        content="test content",
        tenant_id="default",
        fact_type="knowledge",
        tags=[],
        confidence="stated",
        source="api",
        meta={},
        parent_decision_id=None,
    )


@pytest.mark.asyncio
async def test_gateway_router_search_uses_keyword_tenant_scope():
    mock_engine = AsyncMock()
    mock_engine.search.return_value = [
        SimpleNamespace(
            fact_id=1,
            content="hit",
            score=0.91,
            project="project-a",
            fact_type="knowledge",
        )
    ]

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(
        intent=GatewayIntent.SEARCH,
        project="project-a",
        tenant_id="tenant-a",
        payload={"query": "hit", "top_k": 50},
    )

    resp = await router.handle(req)

    assert resp.ok is True
    mock_engine.search.assert_called_once_with(
        query="hit",
        tenant_id="tenant-a",
        project="project-a",
        top_k=20,
    )


@pytest.mark.asyncio
async def test_gateway_router_recall_uses_keyword_tenant_scope():
    mock_engine = AsyncMock()
    mock_engine.recall.return_value = [SimpleNamespace(fact_id=1, content="remembered")]

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(intent=GatewayIntent.RECALL, project="project-a", tenant_id="tenant-a")

    resp = await router.handle(req)

    assert resp.ok is True
    mock_engine.recall.assert_called_once_with(project="project-a", tenant_id="tenant-a")


@pytest.mark.asyncio
async def test_gateway_router_invalid_intent():
    """Verify that GatewayRouter fails gracefully on unknown intent."""
    mock_engine = MagicMock()
    router = GatewayRouter(engine=mock_engine)

    # Bypass enum for testing
    req = GatewayRequest(intent="invalid_intent", payload={})  # type: ignore

    resp = await router.handle(req)

    assert resp.ok is False
    assert "Unknown intent" in resp.error


@pytest.mark.asyncio
async def test_gateway_router_exception_handling():
    """Verify that GatewayRouter captures and returns handler exceptions."""
    mock_engine = AsyncMock()
    mock_engine.search.side_effect = ValueError("Mocked DB failure")

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(intent=GatewayIntent.SEARCH, payload={"query": "test query"})

    resp = await router.handle(req)

    assert resp.ok is False
    assert "Mocked DB failure" in resp.error
    assert resp.latency_ms > 0


@pytest.mark.asyncio
async def test_gateway_router_status_uses_tenant_scope() -> None:
    mock_engine = AsyncMock()
    mock_engine.stats.return_value = {"total_facts": 3, "active_facts": 2, "project_count": 1}

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(intent=GatewayIntent.STATUS, tenant_id="tenant-a", source="mcp")

    resp = await router.handle(req)

    assert resp.ok is True
    assert resp.data["tenant_id"] == "tenant-a"
    mock_engine.stats.assert_called_once_with(tenant_id="tenant-a")
