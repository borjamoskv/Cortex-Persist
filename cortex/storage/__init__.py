"""
CORTEX v5.0 — Storage Backend Abstraction.

Pluggable storage layer: switch between local SQLite and Turso (cloud)
via environment variable. The engine layer never knows which backend
is active — it just calls the protocol methods.

Usage:
    CORTEX_STORAGE=local   → SQLite file (default, current behavior)
    CORTEX_STORAGE=turso   → Turso libSQL cloud
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Protocol, runtime_checkable

logger = logging.getLogger("cortex.storage")


class StorageMode(str, Enum):
    LOCAL = "local"
    TURSO = "turso"
    POSTGRES = "postgres"


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for all storage backends.

    Any backend must implement these methods to be compatible
    with CortexConnectionPool and AsyncCortexEngine.
    """









def get_storage_mode() -> StorageMode:
    """Detect storage mode from environment."""
    raw = os.environ.get("CORTEX_STORAGE", "local").lower()
    try:
        return StorageMode(raw)
    except ValueError:
        logger.warning("Unknown CORTEX_STORAGE='%s', falling back to local", raw)
        return StorageMode.LOCAL


def get_storage_config() -> dict:
    """Gather all storage-related config from environment."""
    mode = get_storage_mode()

    config = {"mode": mode}

    if mode == StorageMode.TURSO:
        url = os.environ.get("TURSO_DATABASE_URL", "")
        token = os.environ.get("TURSO_AUTH_TOKEN", "")

        if not url:
            raise ValueError(
                "TURSO_DATABASE_URL is required when CORTEX_STORAGE=turso. "
                "Example: libsql://your-db.turso.io"
            )
        if not token:
            raise ValueError(
                "TURSO_AUTH_TOKEN is required when CORTEX_STORAGE=turso. "
                "Get it from: turso db tokens create <db-name>"
            )

        config["url"] = url  # type: ignore[reportArgumentType]
        config["token"] = token  # type: ignore[reportArgumentType]

    elif mode == StorageMode.POSTGRES:
        dsn = os.environ.get("POSTGRES_DSN", "")

        if not dsn:
            raise ValueError(
                "POSTGRES_DSN is required when CORTEX_STORAGE=postgres. "
                "Example: postgresql://user:pass@host:5432/cortex"
            )

        config["dsn"] = dsn  # type: ignore[reportArgumentType]

    return config
