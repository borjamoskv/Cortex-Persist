from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from cortex.auth.models import AuthResult
from cortex.extensions.security.security_sync import SecurityVisualSync
from cortex.routes import notch_ws as notch_router


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
    app.include_router(notch_router.router)
    app.state.auth_manager = _FakeAuthManager(auth_map)
    return TestClient(app)


def test_notch_websocket_rejects_missing_api_key() -> None:
    client = _make_client({})

    with client:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/ws/notch"):
                pass

    assert excinfo.value.code == 4401


def test_notch_websocket_accepts_authenticated_client() -> None:
    client = _make_client(
        {
            "ctx_reader": AuthResult(
                authenticated=True,
                tenant_id="tenant-alpha",
                permissions=["read"],
            )
        }
    )

    notch_router.notch_hub._clients.clear()

    with client:
        with client.websocket_connect("/ws/notch?api_key=ctx_reader") as websocket:
            assert notch_router.notch_hub.client_count == 1
            websocket.send_text("pong")

    assert notch_router.notch_hub.client_count == 0


def test_notch_hub_serializes_dict_messages() -> None:
    class _FakeWebSocket:
        def __init__(self) -> None:
            self.messages: list[str] = []

        async def send_text(self, message: str) -> None:
            self.messages.append(message)

    fake_ws = _FakeWebSocket()
    notch_router.notch_hub._clients.clear()
    notch_router.notch_hub._clients.add(fake_ws)

    asyncio.run(notch_router.notch_hub.broadcast({"type": "mood", "value": "calm"}))

    assert fake_ws.messages == [json.dumps({"type": "mood", "value": "calm"})]

    notch_router.notch_hub._clients.clear()


def test_security_visual_sync_uses_notch_hub(monkeypatch) -> None:
    captured: list[dict] = []

    async def _fake_broadcast(message):
        captured.append(message)

    monkeypatch.setattr(notch_router.notch_hub, "broadcast", _fake_broadcast)

    asyncio.run(SecurityVisualSync().emit_signal("threat", {"intensity": 0.8}))

    assert captured == [
        {
            "type": "mood",
            "value": "critical",
            "intensity": 0.8,
            "details": {"intensity": 0.8},
        }
    ]
