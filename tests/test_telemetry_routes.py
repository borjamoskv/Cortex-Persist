from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.routes import telemetry as telemetry_router


class _FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    async def fetchall(self):
        return list(self._rows)

    async def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeConn:
    def __init__(self, rows: list[dict[str, object]], meta_column: str):
        self._rows = rows
        self._meta_column = meta_column

    async def execute(self, sql: str, params=()):
        normalized = " ".join(sql.split())
        if normalized == "PRAGMA table_info(facts)":
            return _FakeCursor(
                [
                    (0, "id"),
                    (1, "tenant_id"),
                    (2, "content"),
                    (3, "fact_type"),
                    (4, self._meta_column),
                ]
            )

        if normalized.startswith("SELECT MAX(id) FROM facts WHERE tenant_id = ? AND fact_type = ?"):
            tenant_id, fact_type = params
            fact_ids = [
                row["id"]
                for row in self._rows
                if row["tenant_id"] == tenant_id and row["fact_type"] == fact_type
            ]
            return _FakeCursor([(max(fact_ids) if fact_ids else None,)])

        if normalized.startswith("SELECT id, content,"):
            tenant_id, fact_type, last_id = params
            matches = [
                (row["id"], row["content"], row.get(self._meta_column))
                for row in sorted(self._rows, key=lambda row: row["id"])
                if row["tenant_id"] == tenant_id
                and row["fact_type"] == fact_type
                and row["id"] > last_id
            ]
            return _FakeCursor(matches)

        raise AssertionError(f"Unexpected SQL in telemetry test: {normalized}")


class _FakeSession:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        return None


class _FakeEngine:
    def __init__(self, rows: list[dict[str, object]], meta_column: str = "metadata"):
        self._conn = _FakeConn(rows, meta_column=meta_column)

    def session(self):
        return _FakeSession(self._conn)


class _FakeAuthManager:
    def __init__(self, key_map: dict[str, AuthResult]):
        self._key_map = key_map

    async def authenticate_async(self, raw_key: str) -> AuthResult:
        return self._key_map.get(
            raw_key,
            AuthResult(authenticated=False, error="Invalid or revoked key"),
        )


def _make_test_client(
    rows: list[dict[str, object]],
    auth_map: dict[str, AuthResult],
    *,
    meta_column: str = "metadata",
) -> TestClient:
    app = FastAPI()
    app.include_router(telemetry_router.router)
    app.dependency_overrides[get_async_engine] = lambda: _FakeEngine(rows, meta_column=meta_column)
    app.state.auth_manager = _FakeAuthManager(auth_map)
    return TestClient(app)


def test_ast_oracle_websocket_rejects_missing_api_key() -> None:
    client = _make_test_client([], {})

    with client:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/telemetry/ast-oracle"):
                pass

    assert excinfo.value.code == 4401


def test_ast_oracle_websocket_is_scoped_to_authenticated_tenant() -> None:
    client = _make_test_client(
        [
            {
                "id": 1,
                "tenant_id": "tenant-beta",
                "fact_type": "human_mutation",
                "content": "beta-only mutation",
                "metadata": json.dumps({"tenant": "tenant-beta"}),
            },
            {
                "id": 2,
                "tenant_id": "tenant-alpha",
                "fact_type": "human_mutation",
                "content": "alpha-only mutation",
                "metadata": json.dumps({"tenant": "tenant-alpha"}),
            },
        ],
        {
            "ctx_alpha": AuthResult(
                authenticated=True,
                tenant_id="tenant-alpha",
                permissions=["read"],
            )
        },
    )

    with client:
        with client.websocket_connect("/telemetry/ast-oracle?api_key=ctx_alpha") as websocket:
            payload = websocket.receive_json()

    assert payload["event"] == "human_mutation"
    assert payload["data"]["fact_id"] == 2
    assert payload["data"]["content"] == "alpha-only mutation"
    assert payload["data"]["meta"] == {"tenant": "tenant-alpha"}


def test_query_new_facts_accepts_legacy_meta_column() -> None:
    engine = _FakeEngine(
        [
            {
                "id": 9,
                "tenant_id": "tenant-alpha",
                "fact_type": "fiat_transaction",
                "content": "invoice settled",
                "meta": json.dumps({"currency": "EUR", "amount": 1250}),
            }
        ],
        meta_column="meta",
    )

    meta_column = asyncio.run(telemetry_router._resolve_facts_meta_column(engine))
    last_id, results = asyncio.run(
        telemetry_router.query_new_facts(
            engine,
            0,
            "fiat_transaction",
            "tenant-alpha",
            meta_column,
        )
    )

    assert last_id == 9
    assert results == [
        {
            "fact_id": 9,
            "content": "invoice settled",
            "meta": {"currency": "EUR", "amount": 1250},
        }
    ]
