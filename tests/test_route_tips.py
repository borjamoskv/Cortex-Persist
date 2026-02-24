"""Tests for CORTEX Tips API route security."""

import pytest
from fastapi.testclient import TestClient

from cortex.api.core import app
from cortex.api.deps import get_engine
from cortex.auth import AuthResult, require_auth

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_overrides():
    """Setup universal overrides for route tests."""

    async def mock_get_engine():
        # TipsEngine handles None engine gracefully for static-only tips
        return None

    app.dependency_overrides[get_engine] = mock_get_engine
    yield
    app.dependency_overrides = {}


def test_get_tips_unauthenticated():
    """Verify that accessing tips without an API key fails."""
    # Ensure require_auth is NOT overridden here to test actual security
    response = client.get("/tips")
    assert response.status_code == 401


def test_get_tips_authenticated():
    """Verify that accessing tips with a valid API key works."""

    async def mock_require_auth():
        return AuthResult(authenticated=True, tenant_id="test", permissions=["read"])

    app.dependency_overrides[require_auth] = mock_require_auth

    response = client.get("/tips")
    assert response.status_code == 200
    assert "tips" in response.json()
