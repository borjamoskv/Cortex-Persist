"""CORTEX Auth — AuthManager and singleton access."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from cortex.auth.backends import BaseAuthBackend
from cortex.auth.models import APIKey, AuthResult

__all__ = ["AuthManager", "get_auth_manager", "reset_auth_manager"]

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages API key authentication for CORTEX.

    Refactored to support multiple storage backends (SQLite, AlloyDB, etc.).
    """

    KEY_LENGTH = 32  # 256-bit keys

    def __init__(self, backend: Optional[BaseAuthBackend | str] = None):
        """Initialize with an optional backend or db_path.

        Args:
            backend: BaseAuthBackend instance, or str (db_path) for SQLite.
        """
        if isinstance(backend, str):
            from cortex.auth.backends import SQLiteAuthBackend

            backend = SQLiteAuthBackend(backend)
        elif backend is None:
            from cortex.config import DB_PATH, PG_URL, RUNBOOT_MODE

            if RUNBOOT_MODE == "cloud" and PG_URL:
                from cortex.auth.backends import AlloyDBAuthBackend

                logger.info("AuthManager: Using Cloud Sovereign (PostgreSQL) backend")
                backend = AlloyDBAuthBackend(PG_URL)
            else:
                from cortex.auth.backends import SQLiteAuthBackend

                logger.info("AuthManager: Using Local Sovereign (SQLite) backend")
                backend = SQLiteAuthBackend(DB_PATH)
        self.backend = backend
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def initialize(self) -> None:
        """Initialize the backend schema (async)."""
        await self.backend.initialize()

# DEPRECATED: Sync methods removed in v6.0 for Sovereign Async Stability.
# Use initialize(), create_key(), and authenticate_async() instead.

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash a raw key for storage/lookup."""
        return hashlib.sha256(key.encode()).hexdigest()

    async def close(self) -> None:
        """Close the backend connections and drain background tasks."""
        if self._background_tasks:
            logger.debug("AuthManager: Draining %d background tasks", len(self._background_tasks))
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()

        if hasattr(self.backend, "close"):
            await self.backend.close()  # type: ignore[reportAttributeAccessIssue]

    async def create_key(
        self,
        name: str,
        tenant_id: str = "default",
        role: str = "user",
        permissions: Optional[list[str]] = None,
        rate_limit: int = 100,
    ) -> tuple[str, APIKey]:
        """Create a new API key. Returns (raw_key, APIKey metadata)."""
        if permissions is None:
            permissions = ["read", "write"]

        raw_key = f"ctx_{secrets.token_hex(self.KEY_LENGTH)}"
        key_hash = self._hash_key(raw_key)
        key_prefix = raw_key[:12]

        key_id = await self.backend.store_key(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            rate_limit=rate_limit,
        )

        new_api_key = APIKey(
            id=key_id,
            name=name,
            key_prefix=key_prefix,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            created_at=datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
            last_used=None,
            is_active=True,
            rate_limit=rate_limit,
        )
        logger.info(
            "Created %s API key '%s' for tenant '%s'",
            role,
            name,
            tenant_id,
        )
        return raw_key, new_api_key

    async def authenticate_async(self, raw_key: str) -> AuthResult:
        """Fully async authentication."""
        is_valid_format = bool(raw_key and raw_key.startswith("ctx_"))
        dummy_hash = self._hash_key("ctx_invalid_dummy_key_to_waste_time")
        key_hash = self._hash_key(raw_key) if is_valid_format else dummy_hash

        if not is_valid_format:
            return AuthResult(authenticated=False, error="Invalid key format")

        row = await self.backend.get_key_by_hash(key_hash)
        if not row:
            return AuthResult(authenticated=False, error="Invalid or revoked key")

        # Background update of last_used
        task = asyncio.create_task(self.backend.update_last_used(row["id"]))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        permissions = row["permissions"]
        if isinstance(permissions, str):
            permissions = json.loads(permissions)

        return AuthResult(
            authenticated=True,
            tenant_id=row["tenant_id"],
            role=row["role"] if "role" in row else "user",
            permissions=permissions,
            key_name=row["name"],
        )

    async def list_keys(self, tenant_id: Optional[str] = None) -> list[APIKey]:
        """List all API keys."""
        rows = await self.backend.list_keys(tenant_id)
        return [
            APIKey(
                id=r["id"],
                name=r["name"],
                key_prefix=r["key_prefix"],
                tenant_id=r["tenant_id"],
                role=r["role"] if "role" in r else "user",
                permissions=json.loads(r["permissions"])
                if isinstance(r["permissions"], str)
                else r["permissions"],
                created_at=r["created_at"],
                last_used=r["last_used"],
                is_active=bool(r["is_active"]),
                rate_limit=r["rate_limit"],
            )
            for r in rows
        ]

    async def revoke_key(self, key_id: int | str) -> bool:
        """Revoke an API key."""
        return await self.backend.revoke_key(key_id)


# ─── Singleton ────────────────────────────────────────────────────────

_auth_manager: AuthManager | None = None
_auth_lock = threading.Lock()


def get_auth_manager() -> AuthManager:
    """Lazy-load the global AuthManager instance (thread-safe)."""
    global _auth_manager  # noqa: PLW0603
    if _auth_manager is None:
        with _auth_lock:
            if _auth_manager is None:
                _auth_manager = AuthManager()
    return _auth_manager


def reset_auth_manager() -> None:
    """Reset the global AuthManager instance (useful for tests)."""
    global _auth_manager  # noqa: PLW0603
    _auth_manager = None
