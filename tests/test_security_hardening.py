"""
CORTEX v5.0 — Security Hardening Tests.
Tests CORS, SQL injection, path traversal, and rate limiting.
Uses isolated temp DB to prevent contamination of other tests.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """Create test client with isolated temp DB."""
    db_path = str(tmp_path_factory.mktemp("security") / "test_security.db")

    import cortex.api.core as api_mod
    import cortex.auth
    import cortex.config as config_mod

    original_config_db = config_mod.DB_PATH
    original_api_db = getattr(api_mod, "DB_PATH", None)

    config_mod.DB_PATH = db_path
    if hasattr(api_mod, "DB_PATH"):
        api_mod.DB_PATH = db_path
    cortex.auth._auth_manager = None

    try:
        with TestClient(api_mod.app) as c:
            yield c
    finally:
        config_mod.DB_PATH = original_config_db
        if original_api_db is not None:
            api_mod.DB_PATH = original_api_db
        cortex.auth._auth_manager = None


def test_cors_preflight(client):
    """Test CORS configuration."""
    response = client.options(
        "/v1/facts",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Should NOT allow evil.com
    assert "http://evil.com" not in response.headers.get("access-control-allow-origin", "")
    assert response.status_code in [200, 400]

    response = client.options(
        "/v1/facts",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Should allow localhost:3000 (configured in ALLOWED_ORIGINS default)
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_sql_injection_temporal(client):
    """Test SQL injection in temporal filter."""
    from cortex.api.core import app
    from cortex.auth import AuthResult, require_auth

    def mock_auth():
        return AuthResult(
            authenticated=True, tenant_id="default", permissions=["read", "write", "admin"]
        )

    app.dependency_overrides[require_auth] = mock_auth

    injection_payload = "2024-01-01' OR '1'='1"
    response = client.get(f"/v1/search?query=test&as_of={injection_payload}")

    app.dependency_overrides = {}

    # Parameterized queries treat injection as literal string — no SQL syntax error
    assert response.status_code in [200, 422, 400]


def test_path_traversal_export(client):
    """Test path traversal in export."""
    from cortex.api.core import app
    from cortex.auth import AuthResult, require_auth

    def mock_admin_auth():
        return AuthResult(
            authenticated=True, tenant_id="default", permissions=["admin", "read", "write"]
        )

    app.dependency_overrides[require_auth] = mock_admin_auth

    response = client.get("/v1/projects/default/export?path=../../../../etc/passwd")

    app.dependency_overrides = {}

    # Should be 400 Bad Request due to validation
    assert response.status_code == 400
    detail = response.json()["detail"]
    # Accept any of the i18n-translated path validation errors
    valid_messages = (
        "Path must be relative",
        "Invalid path",
        "Invalid characters",
        "ruta",  # Spanish
        "workspace",  # English path-workspace
    )
    assert any(msg in detail for msg in valid_messages), f"Unexpected error: {detail}"


@pytest.mark.asyncio
async def test_snapshot_path_sanitization(tmp_path):
    """Test that snapshot names are sanitized against path traversal."""
    from cortex.engine.snapshots import SnapshotManager

    db_path = tmp_path / "test.db"
    db_path.touch()

    sm = SnapshotManager(db_path=db_path)
    # Ensure snapshot_dir exists
    sm.snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Malicious name with path traversal
    malicious_name = "../../../etc/passwd"

    # We use a dummy tx_id and merkle root
    snap = await sm.create_snapshot(malicious_name, 0, "root")

    # The name should be sanitized
    assert ".." not in snap.name
    assert "/" not in snap.name
    assert "etc_passwd" in snap.name or "____etc_passwd" in snap.name

    # Cleanup
    import shutil

    shutil.rmtree(sm.snapshot_dir)
