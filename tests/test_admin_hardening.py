"""
CORTEX v5.1 — Admin Hardening Tests.

Validates the security middleware (rate limiting, audit logging, self-healing)
wired into cortex/routes/admin.py.
"""

import os
import tempfile
from unittest.mock import patch  # noqa: F401 — kept for future admin tests

import pytest
from fastapi.testclient import TestClient

_test_db = tempfile.mktemp(suffix="_admin_hardening.db")


@pytest.fixture(scope="module")
def client():
    """Stand up a fresh TestClient with isolated DB."""
    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(_test_db + ext)
        except FileNotFoundError:
            pass

    import cortex.api.core as api_mod
    import cortex.api.state as api_state
    import cortex.auth
    import cortex.config

    original_db = cortex.config.DB_PATH
    original_env = os.environ.get("CORTEX_DB")

    os.environ["CORTEX_DB"] = _test_db
    cortex.config.DB_PATH = _test_db
    cortex.config.reload()

    cortex.auth.manager._auth_manager = None
    api_state.auth_manager = None
    api_state.engine = None

    try:
        with TestClient(api_mod.app) as c:
            yield c
    finally:
        cortex.config.DB_PATH = original_db
        if original_env is not None:
            os.environ["CORTEX_DB"] = original_env
        else:
            os.environ.pop("CORTEX_DB", None)
        cortex.config.reload()
        cortex.auth.manager._auth_manager = None
        api_state.auth_manager = None
        api_state.engine = None
        for ext in ["", "-wal", "-shm"]:
            try:
                os.unlink(_test_db + ext)
            except FileNotFoundError:
                pass


@pytest.fixture(scope="module")
def api_key(client):
    """Bootstrap an API key (first key needs no auth)."""
    resp = client.post("/v1/admin/keys?name=admin-hardening-test&tenant_id=test")
    if resp.status_code != 200:
        pytest.fail(f"Failed to create key: {resp.text}")
    return resp.json()["key"]


@pytest.fixture(scope="module")
def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


# ─── Rate Limiting Tests ──────────────────────────────────────────────


class TestRateLimiting:
    """Verify the per-IP token-bucket rate limiter."""

    def test_normal_request_succeeds(self, client, auth_headers):
        """A single request should always succeed."""
        resp = client.get("/v1/status", headers=auth_headers)
        assert resp.status_code == 200

    def test_burst_within_limit_succeeds(self, client, auth_headers):
        """Up to 10 requests within the initial bucket should succeed."""
        # The bucket starts full (10 tokens), so 10 rapid requests should pass.
        # We only test a small burst to avoid flakiness.
        statuses = []
        for _ in range(5):
            resp = client.get("/v1/status", headers=auth_headers)
            statuses.append(resp.status_code)
        assert all(s == 200 for s in statuses)


# ─── Audit Logging Tests ─────────────────────────────────────────────


class TestAuditLogging:
    """Verify that the audit logger emits structured log entries."""

    def test_audit_log_emitted(self, client, auth_headers, caplog):
        """Each admin request should produce an AUDIT log line."""
        with caplog.at_level("INFO", logger="cortex.admin.middleware"):
            client.get("/v1/status", headers=auth_headers)
        assert any("AUDIT" in record.message for record in caplog.records)




class TestSelfHealingHookWiring:
    """Quick inline checks for the middleware counter.

    Full SelfHealing coverage lives in test_self_healing.py.
    These are kept here only so the module has at least one non-client
    test (avoids empty class warnings).
    """

    def test_trigger_basic(self):
        from cortex.routes.middleware import _HEAL_COUNTER, SelfHealingHook

        _HEAL_COUNTER.clear()
        SelfHealingHook.trigger(RuntimeError("boom"), {"endpoint": "basic"})
        assert _HEAL_COUNTER.get("basic") == 1

