"""CORTEX Auth — AuthManager and singleton access."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from cortex.auth.backends import BaseAuthBackend
from cortex.auth.models import APIKey, AuthResult

__all__ = ["AuthManager", "get_auth_manager", "reset_auth_manager"]

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages API key authentication for CORTEX.

    Refactored to support multiple storage backends (SQLite, AlloyDB, etc.).
    """

    KEY_LENGTH = 32  # 256-bit keys

    def __init__(self, backend: BaseAuthBackend | str | None = None):
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

    def initialize_sync(self) -> None:
        """Initialize the backend schema (sync)."""
        coro = self.initialize()
        try:
            loop = asyncio.get_running_loop()
            import threading

            event = threading.Event()

            async def _wrapper() -> None:
                await coro
                event.set()

            asyncio.run_coroutine_threadsafe(_wrapper(), loop)
            event.wait()
        except RuntimeError:
            asyncio.run(coro)

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    async def close(self) -> None:
        """Close the backend connections."""
        if hasattr(self.backend, "close"):
            await self.backend.close()

    async def create_key(
        self,
        name: str,
        tenant_id: str = "default",
        role: str = "user",
        permissions: list[str] | None = None,
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
            created_at=datetime.now(timezone.utc).isoformat(),
            last_used=None,
            is_active=True,
            rate_limit=rate_limit,
        )
        logger.info(
            "Created %s API key '%s' for tenant '%s'", role, name, tenant_id,
        )
        return raw_key, new_api_key

    def create_key_sync(
        self,
        name: str,
        tenant_id: str = "default",
        role: str = "user",
        permissions: list[str] | None = None,
        rate_limit: int = 100,
    ) -> tuple[str, APIKey]:
        """Synchronous wrapper for create_key (test fixtures / CLI).

        Handles both 'no event loop' and 'inside existing loop' cases.
        """
        coro = self.create_key(
            name,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            rate_limit=rate_limit,
        )
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        # Inside existing loop — block via thread-safe event
        import threading

        res: list[tuple[str, APIKey]] = []
        err: list[BaseException] = []
        event = threading.Event()

        async def _wrapper() -> None:
            try:
                res.append(await coro)
            except Exception as e:  # noqa: BLE001 — relay to calling thread
                err.append(e)
            finally:
                event.set()

        asyncio.run_coroutine_threadsafe(_wrapper(), loop)
        event.wait()

        if err:
            raise err[0]
        return res[0]

    def authenticate(self, raw_key: str) -> AuthResult:
        """Synchronous wrapper for authentication.

        Authenticate a key synchronously (for legacy test fixtures/CLI).
        In v6 Sovereign Cloud, use authenticate_async whenever possible.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.authenticate_async(raw_key))

        import threading

        res: list[AuthResult] = []
        err: list[BaseException] = []
        event = threading.Event()

        async def _wrapper() -> None:
            try:
                res.append(await self.authenticate_async(raw_key))
            except Exception as e:  # noqa: BLE001 — relay to calling thread
                err.append(e)
            finally:
                event.set()

        asyncio.run_coroutine_threadsafe(_wrapper(), loop)
        event.wait()

        if err:
            raise err[0]
        return res[0]

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

    async def list_keys(self, tenant_id: str | None = None) -> list[APIKey]:
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


def get_auth_manager() -> AuthManager:
    """Lazy-load the global AuthManager instance."""
    global _auth_manager  # noqa: PLW0603
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def reset_auth_manager() -> None:
    """Reset the global AuthManager instance (useful for tests)."""
    global _auth_manager  # noqa: PLW0603
    _auth_manager = None
