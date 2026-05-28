from __future__ import annotations

from collections.abc import Callable

import pytest
from click.testing import CliRunner
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.auth.models import AuthResult
from cortex.cli import cli
from cortex.extensions.llm._presets import _PRESETS_CACHE, provider_inventory
from cortex.routes import ask as ask_router


@pytest.fixture(autouse=True)
def _clear_preset_cache():
    _PRESETS_CACHE.clear()
    yield
    _PRESETS_CACHE.clear()


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def test_provider_inventory_reports_remote_and_local_readiness(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    inventory = {row["provider"]: row for row in provider_inventory(active_provider="openai")}

    assert inventory["openai"]["active"] is True
    assert inventory["openai"]["ready"] is True
    assert inventory["openai"]["api_key_required"] is True
    assert inventory["openai"]["api_key_present"] is True

    assert inventory["anthropic"]["active"] is False
    assert inventory["anthropic"]["ready"] is False
    assert inventory["anthropic"]["status"] == "missing_api_key"
    assert inventory["anthropic"]["reason"] == "Missing env var: ANTHROPIC_API_KEY"

    assert inventory["ollama"]["is_local"] is True
    assert inventory["ollama"]["ready"] is True
    assert inventory["ollama"]["api_key_required"] is False


def test_llm_status_exposes_provider_inventory(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakeProvider:
        model = "gpt-5.4"
        provider_name = "openai"

    class FakeManager:
        available = True
        provider_name = "openai"
        provider = FakeProvider()

    monkeypatch.setattr(ask_router, "_llm_manager", FakeManager())

    app = FastAPI()
    app.include_router(ask_router.router)
    auth_dep = _dependency_for(
        "/v1/llm/status",
        "GET",
        _route_by_path(ask_router.router, "/v1/llm/status", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-llm",
        permissions=["read"],
    )

    with TestClient(app) as client:
        response = client.get("/v1/llm/status")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-5.4"

    providers = {row["provider"]: row for row in body["providers"]}
    assert providers["openai"]["active"] is True
    assert providers["openai"]["ready"] is True
    assert providers["anthropic"]["status"] == "missing_api_key"
    assert "custom" in body["supported_providers"]


def test_routing_status_cli_lists_provider_readiness(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["routing", "status"])

    assert result.exit_code == 0
    assert "LLM Provider Readiness" in result.output
    assert "openai" in result.output
    assert "anthropic" in result.output
    assert "ANTHROPIC_API_KEY" in result.output
