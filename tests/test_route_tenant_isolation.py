from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine, get_engine
from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.routes import admin as admin_router
from cortex.routes import agents as agents_router
from cortex.routes import context as context_router
from cortex.routes import daemon as daemon_router
from cortex.routes import facts as facts_router
from cortex.routes import graph as graph_router
from cortex.routes import ledger as ledger_router
from cortex.routes import oracle as oracle_router
from cortex.routes import trust as trust_router


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class _FakeSession:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *args):
        pass


class _FakeEngine:
    def session(self):
        return _FakeSession()


def test_graph_all_scopes_calls_to_authenticated_tenant(monkeypatch) -> None:
    observed: dict[str, object] = {}

    async def fake_get_graph(
        conn: object,
        project: str | None = None,
        limit: int = 50,
        tenant_id: str = "default",
    ) -> dict[str, object]:
        observed.update({"project": project, "limit": limit, "tenant_id": tenant_id})
        return observed.copy()

    monkeypatch.setattr(graph_router, "_get_graph", fake_get_graph)

    app = FastAPI()
    app.include_router(graph_router.router)
    auth_dep = _dependency_for(
        "/v1/graph", "GET", _route_by_path(graph_router.router, "/v1/graph", "GET")
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-graph",
        permissions=["read"],
    )
    app.dependency_overrides[get_engine] = lambda: _FakeEngine()

    with TestClient(app) as client:
        response = client.get("/v1/graph?limit=25")

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-graph"
    assert observed == {"project": None, "limit": 25, "tenant_id": "tenant-graph"}


class _FakeAsyncEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.register_calls: list[dict[str, str]] = []
        self.list_calls: list[str] = []

    def session(self):
        class AsyncCM:
            async def __aenter__(cm_self):
                return self

            async def __aexit__(cm_self, *args):
                pass

        return AsyncCM()

    async def get_agent(self, agent_id: str, tenant_id: str | None = None) -> dict | None:
        self.calls.append((agent_id, tenant_id))
        if agent_id in {"agent-1", "agent-created"} and tenant_id == "tenant-agents":
            return {
                "id": agent_id,
                "name": "agent-one",
                "agent_type": "ai",
                "reputation_score": 1.0,
                "created_at": "2026-01-01T00:00:00Z",
            }
        return None

    async def register_agent(self, **kwargs):
        self.register_calls.append(kwargs)
        return "agent-created"

    async def list_agents(self, tenant_id: str):
        self.list_calls.append(tenant_id)
        return [
            {
                "id": "agent-1",
                "name": "agent-one",
                "agent_type": "ai",
                "reputation_score": 1.0,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]


class _FakeContextEngine:
    def session(self):
        class AsyncCM:
            async def __aenter__(cm_self):
                return object()

            async def __aexit__(cm_self, *args):
                pass

        return AsyncCM()


class _FakeSignal:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return self._payload


class _FakeContextResult:
    def __init__(self, project: str) -> None:
        self.active_project = project
        self.confidence = "C4"
        self.signals_used = 1
        self.summary = f"project={project}"
        self.top_signals = [
            _FakeSignal(
                {
                    "source": "db:facts",
                    "signal_type": "recent_fact",
                    "content": "tenant-scoped",
                    "project": project,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "weight": 0.9,
                }
            )
        ]
        self.projects_ranked = [(project, 0.9)]


class _FakeOracleEngine:
    def __init__(self) -> None:
        self.store_calls: list[dict[str, object]] = []

    async def store(self, **kwargs) -> None:
        self.store_calls.append(kwargs)


def test_get_agent_scopes_lookup_to_authenticated_tenant() -> None:
    fake_engine = _FakeAsyncEngine()

    app = FastAPI()
    app.include_router(agents_router.router)
    auth_dep = _dependency_for(
        "/v1/agents/{agent_id}",
        "GET",
        _route_by_path(agents_router.router, "/v1/agents/{agent_id}", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-agents",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/agents/agent-1")

    assert response.status_code == 200
    assert response.json()["agent_id"] == "agent-1"
    assert fake_engine.calls == [("agent-1", "tenant-agents")]


def test_register_agent_scopes_creation_to_authenticated_tenant() -> None:
    fake_engine = _FakeAsyncEngine()

    app = FastAPI()
    app.include_router(agents_router.router)
    auth_dep = _dependency_for(
        "/v1/agents",
        "POST",
        _route_by_path(agents_router.router, "/v1/agents", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-agents",
        permissions=["admin"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.post(
            "/v1/agents",
            json={"name": "agent-one", "agent_type": "ai", "public_key": "pub-1"},
        )

    assert response.status_code == 200
    assert fake_engine.register_calls == [
        {
            "name": "agent-one",
            "agent_type": "ai",
            "public_key": "pub-1",
            "tenant_id": "tenant-agents",
        }
    ]
    assert fake_engine.calls == [("agent-created", "tenant-agents")]


def test_list_agents_scopes_listing_to_authenticated_tenant() -> None:
    fake_engine = _FakeAsyncEngine()

    app = FastAPI()
    app.include_router(agents_router.router)
    auth_dep = _dependency_for(
        "/v1/agents",
        "GET",
        _route_by_path(agents_router.router, "/v1/agents", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-agents",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/agents")

    assert response.status_code == 200
    assert fake_engine.list_calls == ["tenant-agents"]


class _FakeFact:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return self._payload


class _FakeFactsManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def recall(
        self,
        project: str,
        tenant_id: str = "default",
        limit: int | None = None,
        offset: int = 0,
    ) -> list[_FakeFact]:
        self.calls.append(
            {
                "project": project,
                "tenant_id": tenant_id,
                "limit": limit,
                "offset": offset,
            }
        )
        return [
            _FakeFact(
                {
                    "id": 1,
                    "project": project,
                    "content": "Export me",
                    "fact_type": "knowledge",
                    "tags": [],
                    "confidence": "stated",
                }
            )
        ]


class _FakeFactsEngine:
    def __init__(self) -> None:
        self.verify_calls: list[str | None] = []
        self.vote_calls: list[dict[str, object]] = []
        self.vote_list_calls: list[tuple[int, str]] = []
        self.deprecate_calls: list[dict[str, object]] = []
        self.causal_chain_calls: list[dict[str, object]] = []
        self.stats_calls: list[str] = []
        self.checkpoint_calls: list[str] = []
        self.facts = _FakeFactsManager()

    async def verify_ledger(self, tenant_id: str | None = None) -> dict[str, object]:
        self.verify_calls.append(tenant_id)
        return {"valid": True, "violations": [], "tx_checked": 7}

    async def stats(self, tenant_id: str = "default") -> dict[str, object]:
        self.stats_calls.append(tenant_id)
        return {
            "total_facts": 10,
            "active_facts": 8,
            "deprecated_facts": 2,
            "project_count": 2,
            "embeddings": 3,
            "transactions": 7,
            "db_size_mb": 1.5,
            "causal_facts": 7,
        }

    async def create_checkpoint(self, tenant_id: str = "default") -> str:
        self.checkpoint_calls.append(tenant_id)
        return f"root:{tenant_id}"

    async def get_fact(self, fact_id: int, tenant_id: str | None = None) -> dict[str, object]:
        return {
            "id": fact_id,
            "tenant_id": tenant_id,
            "project": "tenant-proj",
            "content": "Fact",
            "confidence": "verified",
        }

    async def get_votes(self, fact_id: int, tenant_id: str = "default") -> list[dict[str, object]]:
        self.vote_list_calls.append((fact_id, tenant_id))
        return [{"agent": "agent-one", "vote": 1, "created_at": "2026-01-01T00:00:00Z"}]

    async def deprecate(
        self,
        fact_id: int,
        reason: str | None = None,
        tenant_id: str = "default",
    ) -> bool:
        self.deprecate_calls.append(
            {"fact_id": fact_id, "reason": reason, "tenant_id": tenant_id}
        )
        return True

    async def get_causal_chain(
        self,
        fact_id: int,
        direction: str = "down",
        max_depth: int = 10,
        tenant_id: str = "default",
    ) -> list[dict[str, object]]:
        self.causal_chain_calls.append(
            {
                "fact_id": fact_id,
                "direction": direction,
                "max_depth": max_depth,
                "tenant_id": tenant_id,
            }
        )
        return []

    async def vote_v2(
        self,
        fact_id: int,
        agent_id: str,
        value: int,
        reason: str | None = None,
    ) -> float:
        self.vote_calls.append(
            {
                "fact_id": fact_id,
                "agent_id": agent_id,
                "value": value,
                "reason": reason,
            }
        )
        return 1.75

    async def search(self, *args, **kwargs):
        raise AssertionError("export_project should not call async search")


def test_facts_verify_scopes_ledger_check_to_authenticated_tenant() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/verify",
        "GET",
        _route_by_path(facts_router.router, "/v1/facts/verify", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["read"],
        key_name="agent-one",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/facts/verify")

    assert response.status_code == 200
    assert fake_engine.verify_calls == ["tenant-facts"]


def test_list_votes_scopes_lookup_to_authenticated_tenant() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}/votes",
        "GET",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}/votes", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["read"],
        key_name="agent-one",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/facts/7/votes")

    assert response.status_code == 200
    assert fake_engine.vote_list_calls == [(7, "tenant-facts")]


def test_deprecate_fact_scopes_write_to_authenticated_tenant() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}",
        "DELETE",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}", "DELETE"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["write"],
        key_name="agent-one",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.delete("/v1/facts/7")

    assert response.status_code == 200
    assert fake_engine.deprecate_calls == [
        {"fact_id": 7, "reason": "api deprecated", "tenant_id": "tenant-facts"}
    ]


def test_causal_chain_scopes_read_to_authenticated_tenant() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}/chain",
        "GET",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}/chain", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["read"],
        key_name="agent-one",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/facts/7/chain?direction=up&max_depth=3")

    assert response.status_code == 200
    assert fake_engine.causal_chain_calls == [
        {
            "fact_id": 7,
            "direction": "up",
            "max_depth": 3,
            "tenant_id": "tenant-facts",
        }
    ]


def test_vote_route_binds_internal_agent_identity_to_authenticated_tenant() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}/vote",
        "POST",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}/vote", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["write"],
        key_name="agent-one",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.post("/v1/facts/7/vote", json={"value": 1})

    assert response.status_code == 200
    assert response.json()["agent"] == "agent-one"
    assert fake_engine.vote_calls == [
        {
            "fact_id": 7,
            "agent_id": "tenant-facts:agent-one",
            "value": 1,
            "reason": None,
        }
    ]


def test_vote_v2_rejects_agent_spoofing() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}/vote-v2",
        "POST",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}/vote-v2", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["write"],
        key_name="agent-one",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.post("/v1/facts/7/vote-v2", json={"agent_id": "other-agent", "vote": 1})

    assert response.status_code == 403
    assert fake_engine.vote_calls == []


def test_export_project_uses_tenant_scoped_recall(tmp_path, monkeypatch) -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-admin",
        permissions=["admin"],
        key_name="admin-key",
    )
    app.dependency_overrides[get_engine] = lambda: fake_engine
    monkeypatch.chdir(tmp_path)

    with TestClient(app) as client:
        response = client.get("/v1/projects/demo/export")

    assert response.status_code == 200
    assert fake_engine.facts.calls == [
        {"project": "demo", "tenant_id": "tenant-admin", "limit": 100000, "offset": 0}
    ]
    artifact = tmp_path / "demo_export.json"
    digest_artifact = tmp_path / "demo_export.json.sha256.json"
    assert artifact.exists()
    assert digest_artifact.exists()
    digest_payload = json.loads(digest_artifact.read_text(encoding="utf-8"))
    artifact_bytes = artifact.read_bytes()
    assert response.json()["digest_artifact"] == str(digest_artifact)
    assert response.json()["sha256"] == hashlib.sha256(artifact_bytes).hexdigest()
    assert digest_payload == {
        "artifact": str(artifact),
        "bytes": len(artifact_bytes),
        "facts_count": 1,
        "format": "json",
        "project": "demo",
        "schema": "cortex_project_export_digest_v1",
        "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "tenant_id": "tenant-admin",
    }


def test_status_route_scopes_stats_to_authenticated_tenant() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-admin",
        permissions=["read"],
        key_name="reader-key",
    )
    app.dependency_overrides[get_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/status")

    assert response.status_code == 200
    assert fake_engine.stats_calls == ["tenant-admin"]


def test_compliance_route_scopes_stats_to_authenticated_tenant() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(trust_router.router)
    auth_dep = _dependency_for(
        "/v1/trust/compliance",
        "GET",
        _route_by_path(trust_router.router, "/v1/trust/compliance", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-trust",
        permissions=["admin"],
        key_name="admin-key",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/trust/compliance")

    assert response.status_code == 200
    assert fake_engine.verify_calls == ["tenant-trust"]
    assert fake_engine.stats_calls == ["tenant-trust"]


def test_compliance_route_redacts_backend_failures() -> None:
    class _FailingComplianceEngine(_FakeFactsEngine):
        async def verify_ledger(self, tenant_id: str | None = None) -> dict[str, object]:
            self.verify_calls.append(tenant_id)
            raise sqlite3.DatabaseError("sensitive backend path /tmp/secret.db")

    fake_engine = _FailingComplianceEngine()

    app = FastAPI()
    app.include_router(trust_router.router)
    auth_dep = _dependency_for(
        "/v1/trust/compliance",
        "GET",
        _route_by_path(trust_router.router, "/v1/trust/compliance", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-trust",
        permissions=["admin"],
        key_name="admin-key",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/trust/compliance")

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to generate compliance report"}
    assert fake_engine.verify_calls == ["tenant-trust"]
    assert fake_engine.stats_calls == []


def test_checkpoint_route_scopes_checkpoint_to_authenticated_tenant() -> None:
    fake_engine = _FakeFactsEngine()

    app = FastAPI()
    app.include_router(ledger_router.router)
    auth_dep = _dependency_for(
        "/v1/ledger/checkpoint",
        "POST",
        _route_by_path(ledger_router.router, "/v1/ledger/checkpoint", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-ledger",
        permissions=["admin"],
        key_name="admin-key",
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.post("/v1/ledger/checkpoint")

    assert response.status_code == 200
    assert response.json()["checkpoint_id"] == "root:tenant-ledger"
    assert fake_engine.checkpoint_calls == ["tenant-ledger"]


def test_context_infer_requires_write_permission_when_persisting() -> None:
    app = FastAPI()
    app.include_router(context_router.router)
    auth_dep = _dependency_for(
        "/v1/context/infer",
        "GET",
        _route_by_path(context_router.router, "/v1/context/infer", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-context",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: _FakeContextEngine()

    with TestClient(app) as client:
        response = client.get("/v1/context/infer?persist=true")

    assert response.status_code == 403


def test_context_infer_scopes_runtime_to_authenticated_tenant(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeCollector:
        def __init__(
            self,
            conn: object,
            max_signals: int,
            workspace_dir: str | None,
            git_enabled: bool,
            tenant_id: str = "default",
            include_external: bool = True,
        ) -> None:
            observed["collector"] = {
                "tenant_id": tenant_id,
                "include_external": include_external,
                "git_enabled": git_enabled,
            }

        async def collect_all(self):
            return [
                _FakeSignal(
                    {
                        "source": "db:facts",
                        "signal_type": "recent_fact",
                        "content": "tenant-scoped",
                        "project": "tenant-context",
                        "timestamp": "2026-01-01T00:00:00Z",
                        "weight": 0.9,
                    }
                )
            ]

    class FakeInference:
        def __init__(self, conn: object | None = None, tenant_id: str = "default") -> None:
            observed["inference_init"] = {"tenant_id": tenant_id, "has_conn": conn is not None}
            self.tenant_id = tenant_id

        def infer(self, signals):
            observed["mode"] = "infer"
            observed["signal_count"] = len(signals)
            return _FakeContextResult(self.tenant_id)

        async def infer_and_persist(self, signals):
            observed["mode"] = "persist"
            observed["signal_count"] = len(signals)
            return _FakeContextResult(self.tenant_id)

    monkeypatch.setattr(context_router, "ContextCollector", FakeCollector)
    monkeypatch.setattr(context_router, "ContextInference", FakeInference)

    app = FastAPI()
    app.include_router(context_router.router)
    auth_dep = _dependency_for(
        "/v1/context/infer",
        "GET",
        _route_by_path(context_router.router, "/v1/context/infer", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-context",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: _FakeContextEngine()

    with TestClient(app) as client:
        response = client.get("/v1/context/infer?persist=false")

    assert response.status_code == 200
    assert response.json()["active_project"] == "tenant-context"
    assert observed["collector"] == {
        "tenant_id": "tenant-context",
        "include_external": False,
        "git_enabled": True,
    }
    assert observed["inference_init"] == {"tenant_id": "tenant-context", "has_conn": False}
    assert observed["mode"] == "infer"
    assert observed["signal_count"] == 1


def test_context_history_scopes_lookup_to_authenticated_tenant(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeInference:
        def __init__(self, conn: object | None = None, tenant_id: str = "default") -> None:
            observed["tenant_id"] = tenant_id

        async def get_history(self, limit: int = 10):
            observed["limit"] = limit
            return [{"id": 1, "tenant_id": observed["tenant_id"]}]

    monkeypatch.setattr(context_router, "ContextInference", FakeInference)

    app = FastAPI()
    app.include_router(context_router.router)
    auth_dep = _dependency_for(
        "/v1/context/history",
        "GET",
        _route_by_path(context_router.router, "/v1/context/history", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-context",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: _FakeContextEngine()

    with TestClient(app) as client:
        response = client.get("/v1/context/history?limit=7")

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "tenant_id": "tenant-context"}]
    assert observed == {"tenant_id": "tenant-context", "limit": 7}


def test_oracle_audit_requires_admin_permission() -> None:
    app = FastAPI()
    app.include_router(oracle_router.router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-oracle",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: _FakeOracleEngine()

    with TestClient(app) as client:
        response = client.post(
            "/v1/oracle/audit",
            json={"target_url": "https://example.com/private/path", "agent_type": "ariadne"},
        )

    assert response.status_code == 403


def test_oracle_audit_persists_sanitized_target_metadata(monkeypatch) -> None:
    fake_engine = _FakeOracleEngine()

    class FakeLLMManager:
        available = True

        async def complete(self, **kwargs):
            return "oracle report"

    monkeypatch.setattr(oracle_router, "_llm_manager", FakeLLMManager())

    app = FastAPI()
    app.include_router(oracle_router.router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-oracle",
        permissions=["admin"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.post(
            "/v1/oracle/audit",
            json={
                "target_url": "https://example.com/private/path?q=secret",
                "agent_type": "ariadne",
                "depth": 2,
            },
        )

    assert response.status_code == 200
    assert response.json()["target"] == "https://example.com/private/path?q=secret"
    assert fake_engine.store_calls
    store_call = fake_engine.store_calls[0]
    assert store_call["tenant_id"] == "tenant-oracle"
    assert store_call["tags"] == ["oracle", "ariadne", "https://example.com"]
    assert store_call["meta"]["target_origin"] == "https://example.com"
    assert "target_url" not in store_call["meta"]
    assert "private/path" not in str(store_call["meta"])


def test_daemon_status_requires_admin_permission() -> None:
    app = FastAPI()
    app.include_router(daemon_router.router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-daemon",
        permissions=["read"],
    )

    with TestClient(app) as client:
        response = client.get("/v1/daemon/status")

    assert response.status_code == 403


def test_daemon_status_returns_snapshot_for_admin(monkeypatch) -> None:
    class FakeMoskvDaemon:
        @staticmethod
        def load_status():
            return {"status": "ok", "watchdogs": 3}

    monkeypatch.setattr("cortex.extensions.daemon.MoskvDaemon", FakeMoskvDaemon)

    app = FastAPI()
    app.include_router(daemon_router.router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-daemon",
        permissions=["admin"],
    )

    with TestClient(app) as client:
        response = client.get("/v1/daemon/status")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "watchdogs": 3}


def test_daemon_status_rejects_read_only_keys() -> None:
    app = FastAPI()
    app.include_router(daemon_router.router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-daemon",
        permissions=["read"],
    )

    with TestClient(app) as client:
        response = client.get("/v1/daemon/status")

    assert response.status_code == 403


def test_daemon_status_allows_admin_keys(monkeypatch) -> None:
    from cortex.extensions.daemon.core import MoskvDaemon

    monkeypatch.setattr(
        MoskvDaemon,
        "load_status",
        staticmethod(lambda: {"status": "ok", "daemon": "watchdog"}),
    )

    app = FastAPI()
    app.include_router(daemon_router.router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-daemon",
        permissions=["admin"],
    )

    with TestClient(app) as client:
        response = client.get("/v1/daemon/status")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "daemon": "watchdog"}
