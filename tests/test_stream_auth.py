from __future__ import annotations

import asyncio
import hashlib
from http.cookies import SimpleCookie
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from cortex.api.core import app as core_app
from cortex.api.events import stream_events as legacy_stream_events
from cortex.auth.models import AuthResult
from cortex.auth.stream import (
    STREAM_COOKIE_NAME,
    issue_stream_session_cookie,
    require_stream_auth,
)
from cortex.extensions.signals.models import Signal
from cortex.routes import build_api_router
from cortex.routes import dashboard as dashboard_router
from cortex.routes import events as routes_events
from cortex.api import events as legacy_events


class _FakeAuthManager:
    def __init__(self, key_map: dict[str, AuthResult]):
        self._key_map = key_map
        self.backend = _FakeAuthBackend(key_map)

    async def authenticate_async(self, raw_key: str) -> AuthResult:
        return self._key_map.get(
            raw_key,
            AuthResult(authenticated=False, error="Invalid or revoked key"),
        )


class _FakeAuthBackend:
    def __init__(self, key_map: dict[str, AuthResult]):
        self._rows = {}
        for raw_key, auth in key_map.items():
            self._rows[hashlib.sha256(raw_key.encode("utf-8")).hexdigest()] = {
                "tenant_id": auth.tenant_id,
                "role": auth.role or "user",
                "permissions": auth.permissions,
                "name": raw_key,
            }

    async def get_key_by_hash(self, key_hash: str):
        return self._rows.get(key_hash)


def _make_request(app: FastAPI, *, cookie: str | None = None) -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.encode("utf-8")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/events/stream",
        "headers": headers,
        "query_string": b"",
        "app": app,
    }
    return Request(scope)


def test_require_stream_auth_accepts_bearer_header() -> None:
    app = FastAPI()
    app.state.auth_manager = _FakeAuthManager(
        {
            "ctx_reader": AuthResult(
                authenticated=True,
                tenant_id="tenant-alpha",
                permissions=["read"],
            )
        }
    )
    request = _make_request(app)

    auth = asyncio.run(require_stream_auth(request, authorization="Bearer ctx_reader"))

    assert auth.tenant_id == "tenant-alpha"
    assert auth.permissions == ["read"]


def test_require_stream_auth_accepts_cookie_session() -> None:
    app = FastAPI()
    app.state.auth_manager = _FakeAuthManager(
        {
            "ctx_reader": AuthResult(
                authenticated=True,
                tenant_id="tenant-alpha",
                permissions=["read"],
            )
        }
    )

    response = Response()
    auth = AuthResult(authenticated=True, tenant_id="tenant-alpha", permissions=["read"])
    issue_stream_session_cookie(response, "ctx_reader", auth, secure=False)
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    request = _make_request(app, cookie=f"{STREAM_COOKIE_NAME}={cookie[STREAM_COOKIE_NAME].value}")

    resolved = asyncio.run(require_stream_auth(request, authorization=None))

    assert resolved.tenant_id == "tenant-alpha"
    assert resolved.permissions == ["read"]


def test_stream_session_endpoint_sets_cookie() -> None:
    app = FastAPI()
    app.include_router(routes_events.events_router)
    app.state.auth_manager = _FakeAuthManager(
        {
            "ctx_reader": AuthResult(
                authenticated=True,
                tenant_id="tenant-alpha",
                permissions=["read"],
            )
        }
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/events/session",
            headers={"Authorization": "Bearer ctx_reader"},
        )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-alpha"
    assert STREAM_COOKIE_NAME in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_routes_event_generator_polls_bus_with_tenant_scope() -> None:
    signal = Signal(
        id=7,
        event_type="ledger_append",
        payload={"hash": "abc"},
        source="test",
        project=None,
        tenant_id="tenant-alpha",
        created_at="2026-04-14T00:00:00Z",  # type: ignore[arg-type]
        consumed_by=[],
    )

    class _FakeBus:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        async def poll(self, **kwargs):
            self.calls.append(kwargs)
            return [signal]

    class _FakeRequest:
        def __init__(self):
            self._count = 0

        async def is_disconnected(self):
            self._count += 1
            return False

    bus = _FakeBus()
    engine = SimpleNamespace(_signal_bus=bus)
    request = _FakeRequest()

    gen = routes_events.event_generator(request, engine, "tenant-alpha")
    first = await anext(gen)
    await gen.aclose()

    assert first["event"] == "ledger_append"
    assert bus.calls[0]["tenant_id"] == "tenant-alpha"


@pytest.mark.asyncio
async def test_legacy_event_generator_polls_bus_with_tenant_scope(monkeypatch) -> None:
    signal = Signal(
        id=9,
        event_type="swarm_task",
        payload={"command": "forge test"},
        source="test",
        project=None,
        tenant_id="tenant-beta",
        created_at="2026-04-14T00:00:00Z",  # type: ignore[arg-type]
        consumed_by=[],
    )

    bus_calls: list[dict[str, object]] = []

    class _FakeBus:
        def __init__(self, conn):
            self.calls = bus_calls

        async def poll(self, **kwargs):
            self.calls.append(kwargs)
            return [signal]

    class _Acquire:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args):
            return None

    class _Pool:
        def acquire(self):
            return _Acquire()

    class _FakeRequest:
        def __init__(self):
            self.app = SimpleNamespace(state=SimpleNamespace(pool=_Pool()))
            self._count = 0

        async def is_disconnected(self):
            self._count += 1
            return False

    monkeypatch.setattr(legacy_events, "AsyncSignalBus", _FakeBus)

    request = _FakeRequest()
    gen = legacy_events.event_generator(request, "tenant-beta")
    first = await anext(gen)
    await gen.aclose()

    assert "event: swarm_task" in first
    assert "forge test" in first
    assert bus_calls[0]["tenant_id"] == "tenant-beta"


def test_dashboard_html_bootstraps_cookie_without_localstorage() -> None:
    html = dashboard_router.get_dashboard_html()

    assert "localStorage.getItem('cortex_key')" not in html
    assert "/v1/events/session" in html
    assert "window.history.replaceState" in html
    assert "new EventSource('/v1/events/stream')" in html


def test_core_app_omits_experimental_events_stream_route() -> None:
    matches = [
        route
        for route in core_app.routes
        if getattr(route, "path", None) == "/v1/events/stream"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]

    assert len(matches) == 0


def test_experimental_api_mounts_single_events_stream_route() -> None:
    app = FastAPI()
    app.include_router(build_api_router(include_experimental=True))
    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/v1/events/stream"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]

    assert len(matches) == 1
    assert matches[0].endpoint is not legacy_stream_events
