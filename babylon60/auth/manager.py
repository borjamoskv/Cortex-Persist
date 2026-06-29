# [C5-REAL] Exergy-Maximized

from __future__ import annotations

from babylon60.crypto.hash_registry import cortex_hash
import asyncio
import json
import logging
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from cortex.auth.backends import BaseAuthBackend
from cortex.auth.models import APIKey, AuthResult

import cortex_rs

__all__ = ["AuthManager", "get_auth_manager", "reset_auth_manager"]

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages API key authentication for CORTEX.

    Refactored to support multiple storage backends (SQLite, AlloyDB, etc.).
    """

    KEY_LENGTH = 32  # 256-bit keys

    def __init__(self, backend: BaseAuthBackend | str | None = None) -> None:
        """Initialize with an optional backend or db_path.

        Args:
            backend: BaseAuthBackend instance, or str (db_path) for SQLite.
        """
        if isinstance(backend, str):
            from cortex.auth.backends import SQLiteAuthBackend

            backend = SQLiteAuthBackend(backend)
        elif backend is None:
            from cortex.config import (
                DB_PATH,
                PG_URL,
                RUNBOOT_MODE,
                TURSO_AUTH_TOKEN,
                TURSO_DATABASE_URL,
            )

            if RUNBOOT_MODE == "cloud":
                if TURSO_DATABASE_URL:
                    from cortex.auth.backends import TursoAuthBackend

                    logger.info("AuthManager: Using Cloud Sovereign (Turso) backend")
                    backend = TursoAuthBackend(TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)
                elif PG_URL:
                    from cortex.auth.backends import AlloyDBAuthBackend

                    logger.info("AuthManager: Using Cloud Sovereign (PostgreSQL) backend")
                    backend = AlloyDBAuthBackend(PG_URL)
                else:
                    from cortex.auth.backends import SQLiteAuthBackend

                    logger.info(
                        "AuthManager: Using Local Sovereign (SQLite) backend fallback in Cloud"
                    )
                    backend = SQLiteAuthBackend(DB_PATH)
            else:
                from cortex.auth.backends import SQLiteAuthBackend

                logger.info("AuthManager: Using Local Sovereign (SQLite) backend")
                backend = SQLiteAuthBackend(DB_PATH)
        self.backend = backend
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._background_tasks: set[asyncio.Task[Any]] = set()

        try:
            self._dummy_hash = cortex_rs.hash_password(
                "ctx_dummy_key_to_initialize_hashing_parameters"
            )  # noqa: B009
        except AttributeError:
            self._dummy_hash = "$argon2id$v=19$m=16,t=2,p=1$stub$dummyhash"

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
    def hash_key_legacy_sha256(key: str) -> str:
        return cortex_hash(key.encode())

    async def hash_key_argon2id_async(self, key: str) -> str:
        from cortex.config import AUTH_PEPPER

        loop = asyncio.get_running_loop()
        try:
            hash_fn = getattr(cortex_rs, "hash_password")  # noqa: B009
            return await loop.run_in_executor(self._executor, hash_fn, key + AUTH_PEPPER)
        except AttributeError:
            logger.warning("cortex_rs.hash_password missing. Falling back to stub.")
            return (
                f"$argon2id$v=19$m=16,t=2,p=1$stub${self.hash_key_legacy_sha256(key + AUTH_PEPPER)}"
            )

    async def close(self) -> None:
        """Close the backend connections."""
        if hasattr(self.backend, "close"):
            await self.backend.close()  # type: ignore[reportAttributeAccessIssue]

    async def create_key(
        self,
        name: str,
        tenant_id: str = "default",
        role: str = "viewer",
        permissions: list[str] | None = None,
        rate_limit: int = 100,
    ) -> tuple[str, APIKey]:
        """Create a new API key. Returns (raw_key, APIKey metadata)."""
        if permissions is None:
            permissions = ["read", "write"]

        raw_key = f"ctx_{secrets.token_hex(self.KEY_LENGTH)}"
        key_hash = self.hash_key_legacy_sha256(raw_key)
        key_hash_argon2 = await self.hash_key_argon2id_async(raw_key)
        key_prefix = raw_key[:12]

        key_id = await self.backend.store_key(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            rate_limit=rate_limit,
            key_hash_argon2=key_hash_argon2,
            hash_algo="argon2id",
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

    def create_key_sync(
        self,
        name: str,
        tenant_id: str = "default",
        role: str = "viewer",
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

        # Inside existing loop - block via thread-safe event
        import threading

        res: list[tuple[str, APIKey]] = []
        err: list[BaseException] = []
        event = threading.Event()

        async def _wrapper() -> None:
            try:
                res.append(await coro)
            except (ValueError, TypeError, OSError, KeyError) as e:
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
            except (ValueError, TypeError, OSError, KeyError) as e:
                err.append(e)
            finally:
                event.set()

        asyncio.run_coroutine_threadsafe(_wrapper(), loop)
        event.wait()

        if err:
            raise err[0]
        return res[0]

    async def authenticate_async(self, raw_key: str) -> AuthResult:
        """Fully async authentication with dual-stack Argon2id support."""
        from cortex.config import AUTH_PEPPER

        is_valid_format = bool(raw_key and raw_key.startswith("ctx_"))
        dummy_hash = self.hash_key_legacy_sha256("ctx_invalid_dummy_key_to_waste_time")
        key_hash = self.hash_key_legacy_sha256(raw_key) if is_valid_format else dummy_hash

        if not is_valid_format:
            return AuthResult(authenticated=False, error="Invalid key format")

        row = None
        needs_migration = False

        # 1. Try legacy SHA-256 (fast, uses index)
        legacy_row = await self.backend.get_key_by_hash(key_hash)
        if legacy_row and legacy_row.get("hash_algo", "sha256") == "sha256":
            row = legacy_row
            needs_migration = True
        else:
            # 2. Try Argon2id candidates by prefix
            key_prefix = raw_key[:12]
            candidates = await self.backend.get_key_candidates(key_prefix)

            # Determine the target Argon2 hash: use candidates if present, otherwise fallback to _dummy_hash
            target_hash = self._dummy_hash
            has_candidate = False

            if candidates:
                cand = candidates[0]
                if cand.get("hash_algo") == "argon2id" and cand.get("key_hash_argon2"):
                    target_hash = cand["key_hash_argon2"]
                    has_candidate = True

            is_valid = False
            try:
                loop = asyncio.get_running_loop()
                try:
                    verify_fn = getattr(cortex_rs, "verify_password")  # noqa: B009
                    if verify_fn is None:
                        raise TypeError("verify_password not found")
                    is_valid = await loop.run_in_executor(
                        self._executor,
                        verify_fn,
                        raw_key + AUTH_PEPPER,
                        target_hash,
                    )
                except TypeError:
                    # if getattr returned None
                    stub_hash = f"$argon2id$v=19$m=16,t=2,p=1$stub${self.hash_key_legacy_sha256(raw_key + AUTH_PEPPER)}"
                    is_valid = stub_hash == target_hash
                except AttributeError:
                    stub_hash = f"$argon2id$v=19$m=16,t=2,p=1$stub${self.hash_key_legacy_sha256(raw_key + AUTH_PEPPER)}"
                    is_valid = stub_hash == target_hash
            except Exception as e:
                logger.exception("Cryptographic backend failure during token verification: %s", e)
                is_valid = False

            if is_valid and has_candidate:
                row = candidates[0]

        if not row:
            return AuthResult(authenticated=False, error="Invalid or revoked key")

        # 3. Migrate if needed
        if needs_migration:
            new_hash_argon2 = await self.hash_key_argon2id_async(raw_key)
            task_mig = asyncio.create_task(
                self.backend.migrate_key_to_argon2(row["id"], new_hash_argon2)
            )
            self._background_tasks.add(task_mig)
            task_mig.add_done_callback(self._background_tasks.discard)

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
            role=row["role"] if "role" in row else "viewer",
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
                role=r["role"] if "role" in r else "viewer",
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
    global _auth_manager
    if _auth_manager is None:
        with _auth_lock:
            if _auth_manager is None:
                _auth_manager = AuthManager()
    return _auth_manager


def reset_auth_manager() -> None:
    """Reset the global AuthManager instance (useful for tests)."""
    global _auth_manager
    _auth_manager = None
