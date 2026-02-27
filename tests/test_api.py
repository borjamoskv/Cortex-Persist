import asyncio
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import cortex.api.core as api_mod
import cortex.api.state as api_state
import cortex.auth
from cortex import config
from cortex.auth import AuthManager

# Unique test DB
_test_db_handle = tempfile.NamedTemporaryFile(suffix="_api.db", delete=False)
_test_db = _test_db_handle.name
_test_db_handle.close()


@pytest.fixture(scope="module")
def client():
    """Create test client with a completely isolated database and valid lifespan."""
    # Delete any leftover DB
    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(_test_db + ext)
        except FileNotFoundError:
            pass

    original_db_config = config.DB_PATH
    original_env = os.environ.get("CORTEX_DB")

    # Patch DB path everywhere BEFORE entering lifespan
    os.environ["CORTEX_DB"] = _test_db
    config.DB_PATH = _test_db

    # Inject a mock Master Key for tests so AES encryption doesn't fail
    if not os.environ.get("CORTEX_MASTER_KEY"):
        # Must be exactly 32 bytes for AES-256
        os.environ["CORTEX_MASTER_KEY"] = (
            "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY="  # base64 for 32 bytes
        )

    config.reload()

    # Kill ALL singletons so fresh ones are created
    import cortex.crypto.aes as aes_mod

    aes_mod._default_encrypter_instance = None
    cortex.auth.manager._auth_manager = None
    api_state.auth_manager = None
    api_state.engine = None
    api_state.tracker = None

    # Initialize the DB schema manually for the test DB (required for early auth checks)
    mgr = AuthManager(_test_db)
    asyncio.run(mgr.initialize())

    # Using 'with TestClient(app)' triggers the lifespan protocol
    with TestClient(api_mod.app) as tc:
        yield tc

    # Restore originals
    config.DB_PATH = original_db_config
    config.reload()

    if original_env is not None:
        os.environ["CORTEX_DB"] = original_env
    else:
        os.environ.pop("CORTEX_DB", None)

    # Clean up test DB
    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(_test_db + ext)
        except FileNotFoundError:
            pass


@pytest.fixture(scope="module")
def api_key(client):
    """Create an API key directly via AuthManager."""
    mgr = AuthManager(_test_db)

    async def _setup():
        await mgr.initialize()
        raw_key, _ = await mgr.create_key(
            name="test-key",
            tenant_id="test",
            permissions=["read", "write", "admin"],
        )
        return raw_key

    return asyncio.run(_setup())


@pytest.fixture(scope="module")
def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


class TestHealth:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["service"] == "cortex"

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestAuth:
    def test_no_auth_rejected(self, client):
        resp = client.post("/v1/facts", json={"project": "test", "content": "hello"})
        assert resp.status_code == 401

    def test_bad_key_rejected(self, client):
        resp = client.post(
            "/v1/facts",
            json={"project": "test", "content": "hello"},
            headers={"Authorization": "Bearer ctx_invalid"},
        )
        assert resp.status_code == 401

    def test_good_key_accepted(self, client, auth_headers):
        resp = client.post(
            "/v1/facts",
            json={
                "project": "test",
                "content": "This is a valid test fact for auth verification.",
                "source": "cli",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestFacts:
    def test_store(self, client, auth_headers):
        resp = client.post(
            "/v1/facts",
            json={
                "project": "test",
                "content": "CORTEX uses SQLite with vector search",
                "fact_type": "knowledge",
                "source": "cli",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["fact_id"] > 0
        assert resp.json()["project"] == "test"

    def test_recall(self, client, auth_headers):
        resp = client.get("/v1/projects/test/facts", headers=auth_headers)
        assert resp.status_code == 200
        facts = resp.json()
        assert len(facts) >= 1
        assert any("SQLite" in f["content"] for f in facts)

    def test_deprecate(self, client, auth_headers):
        store_resp = client.post(
            "/v1/facts",
            json={
                "project": "demo",
                "content": "temporary fact",
                "source": "cli",
            },
            headers=auth_headers,
        )
        fact_id = store_resp.json()["fact_id"]

        resp = client.delete(f"/v1/facts/{fact_id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_deprecate_nonexistent(self, client, auth_headers):
        resp = client.delete("/v1/facts/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestSearch:
    def test_search(self, client, auth_headers):
        resp = client.post(
            "/v1/search", json={"query": "database technology", "k": 3}, headers=auth_headers
        )
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)


class TestStatus:
    def test_status(self, client, auth_headers):
        resp = client.get("/v1/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data

    def test_status_requires_auth(self, client):
        resp = client.get("/v1/status")
        assert resp.status_code == 401
