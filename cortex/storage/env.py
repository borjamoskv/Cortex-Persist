"""Cloud/storage environment helpers with backwards-compatible aliases."""

from __future__ import annotations

import os
from collections.abc import Iterable

__all__ = [
    "get_postgres_dsn",
    "get_qdrant_api_key",
    "get_qdrant_url",
    "get_redis_url",
]


def _first_non_empty(keys: Iterable[str]) -> str:
    """Return the first non-empty environment value for the given keys."""
    for key in keys:
        raw = os.environ.get(key, "").strip()
        if raw:
            return raw
    return ""


def get_postgres_dsn() -> str:
    """Resolve PostgreSQL DSN from supported aliases."""
    return _first_non_empty(
        (
            "POSTGRES_DSN",
            "CORTEX_PG_DSN",
            "CORTEX_PG_URL",
            "DATABASE_URL",
            "PG_URL",
        )
    )


def get_qdrant_url(default: str = "http://localhost:6333") -> str:
    """Resolve Qdrant URL from supported aliases."""
    return _first_non_empty(("QDRANT_URL", "CORTEX_QDRANT_URL")) or default


def get_qdrant_api_key() -> str | None:
    """Resolve optional Qdrant API key from supported aliases."""
    key = _first_non_empty(("QDRANT_API_KEY", "CORTEX_QDRANT_API_KEY"))
    return key or None


def get_redis_url(default: str = "redis://localhost:6379/0") -> str:
    """Resolve Redis URL from supported aliases."""
    return _first_non_empty(("REDIS_URL", "CORTEX_REDIS_URL")) or default
