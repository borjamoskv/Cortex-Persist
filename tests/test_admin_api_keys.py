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
def admin_client(tmp_path) -> Iterator[tuple[AuthManager, TestClient]]:
    db_path = tmp_path / "auth.db"
    manager = AuthManager(str(db_path))
    manager.initialize_sync()

    previous_api_manager = api_state.auth_manager
    previous_global_manager = auth_manager_module._auth_manager
    api_state.auth_manager = manager
    auth_manager_module._auth_manager = manager
    admin_router._rate_limiter._buckets.clear()

    app = FastAPI()
    app.include_router(admin_router.router)
    client = TestClient(app)

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
