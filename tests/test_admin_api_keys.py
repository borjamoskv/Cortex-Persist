from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

import cortex.api.state as api_state
import cortex.auth.manager as auth_manager_module
from cortex.auth.manager import AuthManager
from cortex.auth.models import AuthResult
from cortex.routes import admin as admin_router


@pytest.fixture
def admin_client(tmp_path) -> Iterator[tuple[AuthManager, TestClient]]:
    db_path = tmp_path / "auth.db"
    manager = AuthManager(str(db_path))
    asyncio.run(manager.initialize())

    previous_api_manager = api_state.auth_manager
    previous_global_manager = auth_manager_module._auth_manager
    api_state.auth_manager = manager
    auth_manager_module._auth_manager = manager
    admin_router._rate_limiter._buckets.clear()

    app = FastAPI()
    app.include_router(admin_router.router)
    client = TestClient(app, client=("127.0.0.1", 50000))

    try:
        yield manager, client
    finally:
        client.close()
        asyncio.run(manager.close())
        api_state.auth_manager = previous_api_manager
        auth_manager_module._auth_manager = previous_global_manager


def test_create_api_key_bootstrap_is_single_use(admin_client) -> None:
    manager, client = admin_client

    first = client.post(
        "/v1/admin/keys",
        params={"name": "bootstrap-admin", "tenant_id": "tenant-alpha"},
    )
    if first.status_code != 200:
        print(f"DEBUG: {first.json()}")
    assert first.status_code == 200
    assert first.json()["tenant_id"] == "tenant-alpha"

    keys = asyncio.run(manager.list_keys())
    assert len(keys) == 1

    second = client.post(
        "/v1/admin/keys",
        params={"name": "should-fail", "tenant_id": "tenant-alpha"},
    )
    assert second.status_code == 401


def test_create_api_key_remote_bootstrap_without_token_is_denied(admin_client) -> None:
    manager, _ = admin_client

    app = FastAPI()
    app.include_router(admin_router.router)
    remote_client = TestClient(app, client=("203.0.113.10", 50000))
    try:
        response = remote_client.post(
            "/v1/admin/keys",
            params={"name": "remote-admin", "tenant_id": "tenant-alpha"},
        )
    finally:
        remote_client.close()

    assert response.status_code == 403
    assert asyncio.run(manager.list_keys()) == []


def test_create_api_key_remote_bootstrap_accepts_token(admin_client, monkeypatch) -> None:
    manager, _ = admin_client
    monkeypatch.setenv("CORTEX_BOOTSTRAP_TOKEN", "bootstrap-secret")

    app = FastAPI()
    app.include_router(admin_router.router)
    remote_client = TestClient(app, client=("203.0.113.10", 50000))
    try:
        response = remote_client.post(
            "/v1/admin/keys",
            params={"name": "remote-admin", "tenant_id": "tenant-alpha"},
            headers={"Authorization": "Bearer bootstrap-secret"},
        )
    finally:
        remote_client.close()

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-alpha"
    assert len(asyncio.run(manager.list_keys())) == 1


def test_create_api_key_rejects_invalid_tenant_id(admin_client) -> None:
    manager, client = admin_client

    response = client.post(
        "/v1/admin/keys",
        params={"name": "bootstrap-admin", "tenant_id": "tenant alpha"},
    )

    assert response.status_code == 400
    assert asyncio.run(manager.list_keys()) == []


def test_list_api_keys_is_scoped_to_authenticated_tenant(admin_client) -> None:
    manager, client = admin_client

    token_alpha, _ = asyncio.run(
        manager.create_key(
            "alpha-admin",
            tenant_id="tenant-alpha",
            permissions=["read", "write", "admin"],
        )
    )
    asyncio.run(manager.create_key("alpha-worker", tenant_id="tenant-alpha", permissions=["read"]))

    token_beta, _ = asyncio.run(
        manager.create_key(
            "beta-admin",
            tenant_id="tenant-beta",
            permissions=["read", "write", "admin"],
        )
    )
    asyncio.run(manager.create_key("beta-worker", tenant_id="tenant-beta", permissions=["read"]))

    alpha_response = client.get(
        "/v1/admin/keys",
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert alpha_response.status_code == 200
    assert {item["tenant_id"] for item in alpha_response.json()} == {"tenant-alpha"}
    assert {item["name"] for item in alpha_response.json()} == {"alpha-admin", "alpha-worker"}

    beta_response = client.get(
        "/v1/admin/keys",
        headers={"Authorization": f"Bearer {token_beta}"},
    )
    assert beta_response.status_code == 200
    assert {item["tenant_id"] for item in beta_response.json()} == {"tenant-beta"}
    assert {item["name"] for item in beta_response.json()} == {"beta-admin", "beta-worker"}


def test_existing_admin_cannot_create_key_for_other_tenant(admin_client) -> None:
    manager, client = admin_client

    token_alpha, _ = asyncio.run(
        manager.create_key(
            "alpha-admin",
            tenant_id="tenant-alpha",
            permissions=["read", "write", "admin"],
        )
    )

    response = client.post(
        "/v1/admin/keys",
        params={"name": "beta-admin", "tenant_id": "tenant-beta"},
        headers={"Authorization": f"Bearer {token_alpha}"},
    )

    assert response.status_code == 403
    assert {item.tenant_id for item in asyncio.run(manager.list_keys())} == {"tenant-alpha"}


def test_export_project_uses_tenant_scoped_active_facts(monkeypatch, tmp_path) -> None:
    observed: dict[str, str] = {}

    class FakeFact:
        def to_dict(self) -> dict:
            return {"id": 1, "project": "alpha", "content": "tenant fact"}

    class FakeEngine:
        async def get_all_active_facts(self, *, project: str, tenant_id: str):
            observed.update({"project": project, "tenant_id": tenant_id})
            return [FakeFact()]

        async def search(self, *args, **kwargs):
            raise AssertionError("export_project must not call async search through threadpool")

    monkeypatch.chdir(tmp_path)
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 50000)})

    response = asyncio.run(
        admin_router.export_project(
            project="alpha",
            request=request,
            path="alpha_export.json",
            fmt="json",
            auth=AuthResult(authenticated=True, tenant_id="tenant-alpha", permissions=["admin"]),
            engine=FakeEngine(),
        )
    )

    assert observed == {"project": "alpha", "tenant_id": "tenant-alpha"}
    assert response.artifact.endswith("alpha_export.json")
    assert "tenant fact" in (tmp_path / "alpha_export.json").read_text(encoding="utf-8")
