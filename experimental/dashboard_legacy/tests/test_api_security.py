"""Security-focused API contract tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _reload_api_module() -> Any:
    import api

    return importlib.reload(api)


def test_record_fact_requires_tenant_header(monkeypatch) -> None:
    """Write-path calls must supply an explicit tenant header."""
    monkeypatch.setenv("CORTEX_API_KEY", "unit-test-key")
    api = _reload_api_module()
    client = TestClient(api.app)

    response = client.post(
        "/api/facts",
        json={"source": "sdk", "content": "fact"},
        headers={"Authorization": "Bearer unit-test-key"},
    )

    assert response.status_code == 422
    assert "X-Tenant-Id" in response.text


def test_record_fact_fails_closed_without_runtime_api_key(monkeypatch) -> None:
    """Authenticated routes must reject requests when the runtime secret is absent."""
    monkeypatch.delenv("CORTEX_API_KEY", raising=False)
    monkeypatch.delenv("CORTEX_SERVER_API_KEY", raising=False)
    api = _reload_api_module()
    client = TestClient(api.app)

    response = client.post(
        "/api/facts",
        json={"source": "sdk", "content": "fact"},
        headers={
            "Authorization": "Bearer ignored",
            "X-Tenant-Id": "tenant-alpha",
        },
    )

    assert response.status_code == 503


def test_record_fact_accepts_valid_runtime_key(monkeypatch) -> None:
    """A configured runtime secret and tenant header should allow fact writes."""
    captured: dict[str, Any] = {}

    def synthetic_store_fact(tenant_id: str, source: str, content: str, metadata: Any) -> dict[str, str]:
        captured.update(
            {
                "tenant_id": tenant_id,
                "source": source,
                "content": content,
                "metadata": metadata,
            }
        )
        return {"status": "SUCCESS", "id": "hash"}

    monkeypatch.setenv("CORTEX_API_KEY", "unit-test-key")
    api = _reload_api_module()
    monkeypatch.setattr(api, "store_fact", synthetic_store_fact)
    client = TestClient(api.app)

    response = client.post(
        "/api/facts",
        json={"source": "sdk", "content": "fact", "metadata": {"k": "v"}},
        headers={
            "Authorization": "Bearer unit-test-key",
            "X-Tenant-Id": "tenant-alpha",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "SUCCESS", "id": "hash"}
    assert captured["tenant_id"] == "tenant-alpha"
