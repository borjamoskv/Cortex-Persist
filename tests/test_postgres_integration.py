from __future__ import annotations

# [C5-REAL] Exergy-Maximized
import pytest

pytestmark = pytest.mark.integration
"""
Integration tests for PostgreSQL backend integration in FastAPI endpoints.
"""


import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cortex.api.core import app
from cortex.auth.deps import require_auth, require_permission
from cortex.storage import StorageMode


class MockPostgresRecord(dict):
    """Mocks asyncpg.Record which supports attribute access, indexing, and values()."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

    def values(self) -> Any:
        return super().values()


class MockPostgresConnection:
    """Mock asyncpg Connection for testing."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[Any, ...]]] = []
        self.fetch_val: Any = None
        self.fetchrow_val: Any = None
        self.fetch_results: list[Any] = []

    async def execute(self, sql: str, *args: Any) -> str:
        self.queries.append((sql, args))
        return "OK"

    async def fetch(self, sql: str, *args: Any) -> list[Any]:
        self.queries.append((sql, args))
        if "threat_intel" in sql:
            return []
        if "information_schema.columns" in sql:
            import re

            match = re.search(r"table_name\s*=\s*'(.+?)'", sql)
            if match:
                table = match.group(1).lower()
                if table == "facts":
                    cols = [
                        "id",
                        "tenant_id",
                        "project",
                        "content",
                        "fact_type",
                        "tags",
                        "confidence",
                        "valid_from",
                        "valid_until",
                        "source",
                        "meta",
                        "consensus_score",
                        "hash",
                        "signature",
                        "signer_pubkey",
                        "is_quarantined",
                        "quarantined_at",
                        "quarantine_reason",
                        "created_at",
                        "updated_at",
                        "tx_id",
                        "is_tombstoned",
                        "tombstoned_at",
                        "embedding",
                    ]
                    return [
                        MockPostgresRecord(
                            {
                                "cid": 0,
                                "name": c,
                                "type": "text",
                                "notnull": 0,
                                "dflt_value": None,
                                "pk": 0,
                            }
                        )
                        for c in cols
                    ]
                elif table == "signals":
                    cols = [
                        "id",
                        "event_type",
                        "payload",
                        "source",
                        "project",
                        "tenant_id",
                        "created_at",
                        "consumed_by",
                    ]
                    return [
                        MockPostgresRecord(
                            {
                                "cid": 0,
                                "name": c,
                                "type": "text",
                                "notnull": 0,
                                "dflt_value": None,
                                "pk": 0,
                            }
                        )
                        for c in cols
                    ]
        if "embedding <=>" in sql:
            res = []
            for r in self.fetch_results:
                if isinstance(r, dict):
                    v_row = MockPostgresRecord(
                        {
                            "id": r.get("id"),
                            "content": r.get("content"),
                            "project": r.get("project"),
                            "fact_type": r.get("fact_type"),
                            "confidence": r.get("confidence"),
                            "valid_from": r.get("valid_from"),
                            "valid_until": r.get("valid_until"),
                            "tags": r.get("tags"),
                            "source": r.get("source"),
                            "metadata": r.get("metadata") or r.get("meta"),
                            "distance": 0.1,  # distance at index 10
                            "created_at": r.get("created_at"),
                            "updated_at": r.get("updated_at"),
                            "tx_id": r.get("tx_id"),
                            "hash": r.get("hash"),
                        }
                    )
                    res.append(v_row)
                else:
                    res.append(r)
            return res
        return self.fetch_results

    async def fetchrow(self, sql: str, *args: Any) -> Any:
        self.queries.append((sql, args))
        return self.fetchrow_val

    async def executemany(self, sql: str, args_list: list[Any]) -> str:
        for args in args_list:
            self.queries.append((sql, args))
        return "OK"

    def transaction(self) -> MagicMock:
        tx = MagicMock()
        tx.__aenter__ = AsyncMock()
        tx.__aexit__ = AsyncMock()
        return tx


class MockAcquireContext:
    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def __aenter__(self) -> Any:
        return self._conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def __await__(self) -> Any:
        async def _await():
            return self._conn

        return _await().__await__()


class MockPostgresPool:
    """Mock asyncpg Pool for testing."""

    def __init__(self, conn: MockPostgresConnection) -> None:
        self._conn = conn

    def acquire(self) -> MockAcquireContext:
        return MockAcquireContext(self._conn)

    async def release(self, conn: Any) -> None:
        pass

    async def close(self) -> None:
        pass


@pytest.fixture
def mock_postgres_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_STORAGE", "postgres")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://user:pass@host:5432/cortex")
    monkeypatch.setattr("cortex.storage.get_storage_mode", lambda: StorageMode.POSTGRES)
    monkeypatch.setattr("cortex.search.vector.get_storage_mode", lambda: StorageMode.POSTGRES)
    monkeypatch.setattr("cortex.search.text.get_storage_mode", lambda: StorageMode.POSTGRES)
    monkeypatch.setattr("cortex.config.DEPLOY_MODE", "cloud")


def test_postgres_api_endpoints(mock_postgres_env: None) -> None:
    mock_conn = MockPostgresConnection()
    mock_pool = MockPostgresPool(mock_conn)

    # Set mock return values
    # For facts SELECT duplicate check in store
    mock_conn.fetchrow_val = None

    # Mock AuthResult
    mock_auth = MagicMock()
    mock_auth.tenant_id = "default"
    mock_auth.authenticated = True
    mock_auth.permissions = ["read", "write", "admin"]
    mock_auth.key_name = "test_agent"

    async def override_auth() -> MagicMock:
        return mock_auth

    # Override dependencies
    app.dependency_overrides[require_auth] = override_auth
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth

    # Mock create_pool_async and PostgresBackend.connect/initialize_schema
    with (
        patch("cortex.database.postgres_core.create_pool_async", return_value=mock_pool),
        patch("cortex.storage.postgres.PostgresBackend.connect", new_callable=AsyncMock),
        patch("cortex.storage.postgres.PostgresBackend.close", new_callable=AsyncMock),
        patch("cortex.api.core.CortexEngine.init_db", new_callable=AsyncMock),
        patch("cortex.api.core.CortexEngine.close", new_callable=AsyncMock),
    ):
        with TestClient(app) as client:
            # 1. Test Store Fact Endpoint
            print("\nPOOL TYPE:", type(app.state.pool))
            mock_conn.fetchrow_val = MockPostgresRecord({"id": 123})
            store_payload = {
                "project": "test-proj",
                "content": "Sovereign memory is running on PostgreSQL",
                "fact_type": "knowledge",
                "tags": ["postgres", "test"],
                "source": "api-agent",
            }
            resp = client.post("/v1/facts", json=store_payload)
            assert resp.status_code == 200
            assert resp.json()["fact_id"] == "123"
            assert resp.json()["message"] == "Fact stored"

            # Check that query translations occurred (translated to $ placeholders and contains ON CONFLICT)
            stored_queries = [q for q, _ in mock_conn.queries]
            assert any("INSERT INTO facts" in q and "$1" in q for q in stored_queries)
            assert any(
                "INSERT INTO fact_tags" in q and "ON CONFLICT DO NOTHING" in q
                for q in stored_queries
            )

            # 2. Test Recall Facts / Search Endpoint
            now = datetime.datetime.now(datetime.timezone.utc)
            mock_row = MockPostgresRecord(
                {
                    "id": 999,
                    "content": "Mocked fact content",
                    "project": "test-proj",
                    "fact_type": "knowledge",
                    "confidence": "C5",
                    "valid_from": "2026-06-06T00:00:00Z",
                    "valid_until": None,
                    "tags": ["postgres"],
                    "source": "api-agent",
                    "metadata": {"foo": "bar"},
                    "created_at": now,
                    "updated_at": now,
                    "tx_id": 101,
                    "hash": "tx-hash-999",
                    "consensus_score": 1.0,
                    "confidence_rank": 5.0,
                }
            )
            mock_conn.fetch_results = [mock_row]

            search_payload = {
                "query": "PostgreSQL",
                "k": 5,
                "project": "test-proj",
            }
            resp = client.post("/v1/facts/search", json=search_payload)
            assert resp.status_code == 200
            results = resp.json()
            assert len(results) == 1
            assert results[0]["id"] == "999"
            assert results[0]["content"] == "Mocked fact content"

            search_queries = [q for q, _ in mock_conn.queries]
            assert any("ILIKE" in q and "facts" in q for q in search_queries)

    app.dependency_overrides.clear()
