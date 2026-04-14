from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from cortex.auth.models import AuthResult
from cortex.routes import topology_ws as topology_router


class _FakeAuthManager:
    def __init__(self, key_map: dict[str, AuthResult]):
        self._key_map = key_map

    async def authenticate_async(self, raw_key: str) -> AuthResult:
        return self._key_map.get(
            raw_key,
            AuthResult(authenticated=False, error="Invalid or revoked key"),
        )


def _make_client(auth_map: dict[str, AuthResult]) -> TestClient:
    app = FastAPI()
    app.include_router(topology_router.router)
    app.state.auth_manager = _FakeAuthManager(auth_map)
    return TestClient(app)


def test_topology_websocket_rejects_missing_api_key() -> None:
    client = _make_client({})

    with client:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/ws/v1/topology"):
                pass

    assert excinfo.value.code == 4401


def test_topology_websocket_accepts_authenticated_client() -> None:
    client = _make_client(
        {
            "ctx_reader": AuthResult(
                authenticated=True,
                tenant_id="tenant-alpha",
                permissions=["read"],
            )
        }
    )

    topology_router.topology_manager.active_connections.clear()
    topology_router.topology_manager._tenant_connections.clear()

    with client:
        with client.websocket_connect("/ws/v1/topology?api_key=ctx_reader") as websocket:
            assert len(topology_router.topology_manager.active_connections) == 1
            websocket.send_text('{"type":"INJECT_NOISE","node_id":"node-7"}')

    assert topology_router.topology_manager.active_connections == []


def test_topology_websocket_accepts_bearer_header() -> None:
    client = _make_client(
        {
            "ctx_reader": AuthResult(
                authenticated=True,
                tenant_id="tenant-alpha",
                permissions=["read"],
            )
        }
    )

    topology_router.topology_manager.active_connections.clear()
    topology_router.topology_manager._tenant_connections.clear()

    with client:
        with client.websocket_connect(
            "/ws/v1/topology", headers={"authorization": "Bearer ctx_reader"}
        ) as websocket:
            assert len(topology_router.topology_manager.active_connections) == 1
            websocket.send_text('{"type":"INJECT_NOISE","node_id":"node-7"}')

    assert topology_router.topology_manager.active_connections == []


def test_topology_websocket_rejects_invalid_api_key() -> None:
    client = _make_client({})

    with client:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/ws/v1/topology?api_key=ctx_bogus"):
                pass

    assert excinfo.value.code == 4401


def test_topology_manager_broadcasts_only_to_same_tenant() -> None:
    class _FakeWebSocket:
        def __init__(self) -> None:
            self.accepted = False
            self.messages: list[str] = []

        async def accept(self) -> None:
            self.accepted = True

        async def send_text(self, message: str) -> None:
            self.messages.append(message)

    manager = topology_router.TopologyManager()
    alpha = _FakeWebSocket()
    beta = _FakeWebSocket()

    async def _exercise() -> None:
        await manager.connect(alpha, "tenant-alpha")
        await manager.connect(beta, "tenant-beta")
        await manager.broadcast_event("NEW_NODE", {"node_id": "n-1"}, tenant_id="tenant-alpha")

    import asyncio

    asyncio.run(_exercise())

    assert alpha.accepted is True
    assert beta.accepted is True
    assert len(alpha.messages) == 1
    assert beta.messages == []
