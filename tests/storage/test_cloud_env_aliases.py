from __future__ import annotations

from cortex.storage.env import (
    get_postgres_dsn,
    get_qdrant_api_key,
    get_qdrant_url,
    get_redis_url,
)


def test_get_postgres_dsn_prefers_primary_alias(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://primary")
    monkeypatch.setenv("DATABASE_URL", "postgresql://fallback")
    assert get_postgres_dsn() == "postgresql://primary"


def test_get_postgres_dsn_falls_back_to_database_url(monkeypatch) -> None:
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.delenv("CORTEX_PG_DSN", raising=False)
    monkeypatch.delenv("CORTEX_PG_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://db-url")
    assert get_postgres_dsn() == "postgresql://db-url"


def test_get_qdrant_aliases(monkeypatch) -> None:
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.setenv("CORTEX_QDRANT_URL", "https://qdrant.example.com")
    monkeypatch.setenv("CORTEX_QDRANT_API_KEY", "secret")
    assert get_qdrant_url() == "https://qdrant.example.com"
    assert get_qdrant_api_key() == "secret"


def test_get_redis_aliases_and_default(monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CORTEX_REDIS_URL", raising=False)
    assert get_redis_url() == "redis://localhost:6379/0"

    monkeypatch.setenv("CORTEX_REDIS_URL", "redis://cache:6379/1")
    assert get_redis_url() == "redis://cache:6379/1"
