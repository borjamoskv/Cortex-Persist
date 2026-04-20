from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import cortex.api.state as api_state
import cortex.auth.manager as auth_manager_module
from cortex.auth.manager import AuthManager
from cortex.routes import admin as admin_router


@pytest.fixture
def admin_manager(tmp_path, monkeypatch) -> Iterator[AuthManager]:
    db_path = tmp_path / "auth.db"
    manager = AuthManager(str(db_path))
    manager.initialize_sync()

    previous_api_manager = api_state.auth_manager
    previous_global_manager = auth_manager_module._auth_manager
    api_state.auth_manager = manager
    auth_manager_module._auth_manager = manager
    admin_router._rate_limiter._buckets.clear()
    monkeypatch.delenv("CORTEX_BOOTSTRAP_TOKEN", raising=False)

    try:
        yield manager
    finally:
        asyncio.run(manager.close())
        api_state.auth_manager = previous_api_manager
        auth_manager_module._auth_manager = previous_global_manager


def _build_admin_client(client_host: str = "testclient") -> TestClient:
    app = FastAPI()
    app.include_router(admin_router.router)
    return TestClient(app, client=(client_host, 50000))


def test_bootstrap_remote_rejected_without_valid_bootstrap_condition(admin_manager) -> None:
    manager = admin_manager
    with _build_admin_client(client_host="192.168.1.44") as client:
        response = client.post(
            "/v1/admin/keys",
            params={"name": "bootstrap-admin", "tenant_id": "tenant-alpha"},
        )

    assert response.status_code == 403
    assert asyncio.run(manager.list_keys()) == []


def test_bootstrap_local_allowed_when_uninitialized(admin_manager) -> None:
    manager = admin_manager
    with _build_admin_client(client_host="127.0.0.1") as client:
        response = client.post(
            "/v1/admin/keys",
            params={"name": "bootstrap-admin", "tenant_id": "tenant-alpha"},
        )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-alpha"
    assert len(asyncio.run(manager.list_keys())) == 1


def test_bootstrap_allowed_with_cortex_bootstrap_token(admin_manager, monkeypatch) -> None:
    manager = admin_manager
    bootstrap_token = "bootstrap-secret-token"
    monkeypatch.setenv("CORTEX_BOOTSTRAP_TOKEN", bootstrap_token)

    with _build_admin_client(client_host="203.0.113.15") as client:
        response = client.post(
            "/v1/admin/keys",
            params={"name": "bootstrap-admin", "tenant_id": "tenant-alpha"},
            headers={"X-Cortex-Bootstrap-Token": bootstrap_token},
        )

    assert response.status_code == 200
    assert len(asyncio.run(manager.list_keys())) == 1


def test_create_api_key_bootstrap_is_single_use(admin_manager) -> None:
    manager = admin_manager
    with _build_admin_client(client_host="127.0.0.1") as client:
        first = client.post(
            "/v1/admin/keys",
            params={"name": "bootstrap-admin", "tenant_id": "tenant-alpha"},
        )
        assert first.status_code == 200
        second = client.post(
            "/v1/admin/keys",
            params={"name": "should-fail", "tenant_id": "tenant-alpha"},
        )

    assert first.json()["tenant_id"] == "tenant-alpha"
    assert len(asyncio.run(manager.list_keys())) == 1
    assert second.status_code == 401


def test_create_api_key_rejects_invalid_tenant_id(admin_manager) -> None:
    manager = admin_manager
    with _build_admin_client(client_host="127.0.0.1") as client:
        response = client.post(
            "/v1/admin/keys",
            params={"name": "bootstrap-admin", "tenant_id": "tenant alpha"},
        )

    assert response.status_code == 400
    assert asyncio.run(manager.list_keys()) == []


def test_list_api_keys_is_scoped_to_authenticated_tenant(admin_manager) -> None:
    manager = admin_manager

    token_alpha, _ = manager.create_key_sync(
        "alpha-admin",
        tenant_id="tenant-alpha",
        permissions=["read", "write", "admin"],
    )
    manager.create_key_sync("alpha-worker", tenant_id="tenant-alpha", permissions=["read"])

    token_beta, _ = manager.create_key_sync(
        "beta-admin",
        tenant_id="tenant-beta",
        permissions=["read", "write", "admin"],
    )
    manager.create_key_sync("beta-worker", tenant_id="tenant-beta", permissions=["read"])

    with _build_admin_client(client_host="127.0.0.1") as client:
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
