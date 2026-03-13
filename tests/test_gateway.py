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
    mock_engine.store.assert_called_once()


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
