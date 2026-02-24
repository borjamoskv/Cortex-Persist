import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from cortex.api.core import app

_test_db = tempfile.mktemp(suffix="_translate.db")


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    import cortex.config

    original_db_config = cortex.config.DB_PATH

    os.environ["CORTEX_DB"] = _test_db
    cortex.config.DB_PATH = _test_db
    cortex.config.reload()

    with TestClient(app) as test_client:
        yield test_client

    cortex.config.DB_PATH = original_db_config
    cortex.config.reload()
    os.environ.pop("CORTEX_DB", None)

    # Clean up test DB
    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(_test_db + ext)
        except OSError:
            pass


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict[str, str]:
    from cortex.auth import AuthManager

    mgr = AuthManager(_test_db)
    raw_key, _ = mgr.create_key(
        name="test-translate-key",
        tenant_id="test",
        permissions=["read", "write"],
    )
    return {"Authorization": f"Bearer {raw_key}"}


def test_translate_validation_error(client: TestClient, auth_headers: dict[str, str]) -> None:
    # Test missing required fields
    response = client.post(
        "/v1/translate", json={"texts": {"hello": "world"}}, headers=auth_headers
    )
    assert response.status_code == 422  # pydantic validation error

    response = client.post("/v1/translate", json={"target_languages": ["es"]}, headers=auth_headers)
    assert response.status_code == 422


def test_translate_too_many_texts(client: TestClient, auth_headers: dict[str, str]) -> None:
    # Test over 100 items restriction
    large_texts = {str(i): "word" for i in range(101)}
    response = client.post(
        "/v1/translate",
        json={"texts": large_texts, "target_languages": ["es"]},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Maximum 100 texts allowed per request" in response.text


def test_translate_unauthorized(client: TestClient) -> None:
    response = client.post(
        "/v1/translate", json={"texts": {"hello": "world"}, "target_languages": ["es"]}
    )
    assert response.status_code == 401
