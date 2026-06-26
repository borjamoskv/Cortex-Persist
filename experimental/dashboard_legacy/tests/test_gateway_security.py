"""Gateway hardening tests for auth and exergy handling."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _reload_gateway_module():
    import mcp_saas.gateway

    return importlib.reload(mcp_saas.gateway)


def test_gateway_returns_503_when_token_store_is_missing(monkeypatch) -> None:
    """The MCP membrane must fail closed if no runtime token store is configured."""
    monkeypatch.delenv("CORTEX_MCP_TOKENS_FILE", raising=False)
    monkeypatch.delenv("CORTEX_TOKEN_STORE", raising=False)
    gateway = _reload_gateway_module()
    client = TestClient(gateway.app)

    response = client.post(
        "/api/mcp/message",
        params={"token": "missing"},
        json={"method": "tools/call", "params": {"name": "intel_brief"}},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "TOKEN_STORE_UNAVAILABLE"


def test_gateway_does_not_deduct_exergy_for_unconfigured_capability(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Missing local servers must not burn exergy from a valid tenant token."""
    token_store = tmp_path / "tokens.yaml"
    token_store.write_text(
        yaml.safe_dump(
            {
                "unit-test-token": {
                    "capabilities": ["vsa"],
                    "exergy_balance": "10.0",
                    "tenant_id": "tenant-alpha",
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("CORTEX_MCP_TOKENS_FILE", str(token_store))
    gateway = _reload_gateway_module()
    monkeypatch.setattr(gateway, "record_memory_event", lambda *args, **kwargs: None)
    client = TestClient(gateway.app)

    response = client.post(
        "/api/mcp/message",
        params={"token": "unit-test-token"},
        json={"method": "tools/call", "params": {"name": "vsa_scan", "arguments": {}}, "id": 7},
    )

    assert response.status_code == 200
    assert response.json()["error"] == "Server not configured for capability"

    reloaded = yaml.safe_load(token_store.read_text(encoding="utf-8"))
    assert reloaded["unit-test-token"]["exergy_balance"] == "10.0"
