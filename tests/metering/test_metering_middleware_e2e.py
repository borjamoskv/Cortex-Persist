from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import cortex.auth.manager as auth_manager_module
from cortex.auth import AuthResult, require_permission
from cortex.auth.manager import AuthManager
from cortex.extensions.metering.middleware import MeteringMiddleware
from cortex.extensions.metering.quotas import PLAN_QUOTAS, PlanQuota
from cortex.extensions.metering.tracker import UsageTracker


@pytest.fixture
def metered_client(tmp_path) -> Iterator[tuple[TestClient, str, str, str]]:
    auth_db_path = tmp_path / "auth_metering.db"
    usage_db_path = tmp_path / "usage_metering.db"

    auth_manager = AuthManager(str(auth_db_path))
    auth_manager.initialize_sync()
    token_a, _ = auth_manager.create_key_sync(
        "metering-tenant-a",
        tenant_id="tenant_metering_a",
        permissions=["read"],
    )
    token_b, _ = auth_manager.create_key_sync(
        "metering-tenant-b",
        tenant_id="tenant_metering_b",
        permissions=["read"],
    )

    previous_manager = auth_manager_module._auth_manager
    auth_manager_module._auth_manager = auth_manager

    old_free = PLAN_QUOTAS["free"]
    PLAN_QUOTAS["free"] = PlanQuota(
        name="free",
        calls_limit=2,
        projects_limit=old_free.projects_limit,
        storage_bytes=old_free.storage_bytes,
        rate_limit=old_free.rate_limit,
        search_depth=old_free.search_depth,
        batch_size=old_free.batch_size,
        ledger_verify=old_free.ledger_verify,
    )

    tracker = UsageTracker(db_path=str(usage_db_path))
    app = FastAPI()
    app.add_middleware(MeteringMiddleware, tracker=tracker)

    @app.get("/v1/ping")
    async def ping(_: AuthResult = Depends(require_permission("read"))) -> dict[str, str]:
        return {"ok": "true"}

    client = TestClient(app)

    try:
        yield client, token_a, token_b, str(usage_db_path)
    finally:
        PLAN_QUOTAS["free"] = old_free
        auth_manager_module._auth_manager = previous_manager
        client.close()
        try:
            tracker.close()
        except sqlite3.ProgrammingError:
            # TestClient serves requests in a different thread.
            # Tracker cleanup is best-effort in this fixture.
            pass
        asyncio.run(auth_manager.close())


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_metering_requires_valid_auth_before_quota_check(metered_client) -> None:
    client, _, _, _usage_db_path = metered_client
    response = client.get("/v1/ping")
    assert response.status_code == 401


def test_quota_enforcement_is_per_tenant(metered_client) -> None:
    client, token_a, token_b, usage_db_path = metered_client

    # Tenant A reaches free-tier limit (2 calls).
    assert client.get("/v1/ping", headers=_auth_headers(token_a)).status_code == 200
    assert client.get("/v1/ping", headers=_auth_headers(token_a)).status_code == 200
    quota_hit = client.get("/v1/ping", headers=_auth_headers(token_a))
    assert quota_hit.status_code == 429
    assert quota_hit.json()["error"] == "quota_exceeded"

    # Tenant B remains unaffected by tenant A usage.
    assert client.get("/v1/ping", headers=_auth_headers(token_b)).status_code == 200

    inspector = UsageTracker(db_path=usage_db_path)
    try:
        usage_a = inspector.get_usage("tenant_metering_a")
        usage_b = inspector.get_usage("tenant_metering_b")
        assert usage_a["calls_used"] == 2
        assert usage_b["calls_used"] == 1
    finally:
        inspector.close()
