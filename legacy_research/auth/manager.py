# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import cortex_rs
from cortex.auth.backends import BaseAuthBackend
from cortex.auth.models import APIKey, AuthResult

# Hashing fallback: use Rust-native if present, otherwise fall back to Python argon2-cffi
try:
    hash_password = cortex_rs.hash_password
    verify_password = cortex_rs.verify_password
    HAS_RUST_AUTH = True
except AttributeError:
    HAS_RUST_AUTH = False
    try:
        import argon2
        _ph = argon2.PasswordHasher(
            time_cost=2,
            memory_cost=65536,
            parallelism=1,
            hash_len=32,
        )
        def hash_password(password: str) -> str:
            return _ph.hash(password)
        def verify_password(password: str, hash_str: str) -> bool:
            try:
                return _ph.verify(hash_str, password)
            except Exception:
                return False
    except ImportError:
        # Extreme fallback to SHA-256 if argon2 is completely missing
        def hash_password(password: str) -> str:
            return hashlib.sha256(password.encode()).hexdigest()
        def verify_password(password: str, hash_str: str) -> bool:
            return hashlib.sha256(password.encode()).hexdigest() == hash_str

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
        return hashlib.sha256(key.encode()).hexdigest()

    async def hash_key_argon2id_async(self, key: str) -> str:
        from cortex.config import AUTH_PEPPER

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            hash_password,
            key + AUTH_PEPPER
        )

    async def close(self) -> None:
        """Close the backend connections."""
        if hasattr(self.backend, "close"):
            await self.backend.close()  # type: ignore[reportAttributeAccessIssue]

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

        # Inside existing loop - block via thread-safe event
        import threading

        res: list[tuple[str, APIKey]] = []
        err: list[BaseException] = []
        event = threading.Event()

        async def _wrapper() -> None:
            try:
                res.append(await coro)
            except Exception as e:
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
            except Exception as e:
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
            for cand in candidates:
                if cand.get("hash_algo") == "argon2id" and cand.get("key_hash_argon2"):
                    try:
                        loop = asyncio.get_running_loop()
                        is_valid = await loop.run_in_executor(
                            self._executor,
                            verify_password,
                            raw_key + AUTH_PEPPER,
                            cand["key_hash_argon2"]
                        )
                        if is_valid:
                            row = cand
                            break
                    except Exception:
                        pass

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
