"""
CORTEX v5.0 — Authentication & Authorization.

API key management with SHA-256 hashing. Keys are stored hashed,
never in plaintext. Supports scoped permissions per tenant.
"""

import asyncio
import hashlib
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, Request

from cortex.auth.backends import BaseAuthBackend
from cortex.auth.rbac import RBAC, Permission

__all__ = [
    "APIKey",
    "AUTH_SCHEMA",
    "AuthManager",
    "AuthResult",
    "SQL_INSERT_KEY",
    "get_auth_manager",
    "require_auth",
    "require_permission",
    "require_consensus",
    "require_verified_permission",
]

logger = logging.getLogger(__name__)

# ─── Schema ───────────────────────────────────────────────────────────

AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    key_hash    TEXT NOT NULL UNIQUE,
    key_prefix  TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    role        TEXT NOT NULL DEFAULT 'user',
    permissions TEXT NOT NULL DEFAULT '["read","write"]',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_used   TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    rate_limit  INTEGER NOT NULL DEFAULT 100
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
"""

SQL_INSERT_KEY = """
    INSERT INTO api_keys (name, key_hash, key_prefix, tenant_id, role, permissions, rate_limit)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""


# ─── Auth Model & Manager ─────────────────────────────────────────────


@dataclass
class APIKey:
    """Represents an API key with its metadata."""

    id: int | str
    name: str
    key_prefix: str
    tenant_id: str
    role: str
    permissions: list[str]
    created_at: str
    last_used: str | None
    is_active: bool
    rate_limit: int


@dataclass
class AuthResult:
    """Result of an authentication attempt."""

    authenticated: bool
    tenant_id: str = "default"
    role: str = "user"
    permissions: list[str | Permission] = field(default_factory=list)
    key_name: str = ""
    error: str = ""


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
        self._background_tasks: set[asyncio.Task] = set()

    async def initialize(self) -> None:
        """Initialize the backend schema (async)."""
        await self.backend.initialize()

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
        logger.info("Created %s API key '%s' for tenant '%s'", role, name, tenant_id)
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

        # Inside existing loop (e.g. FastAPI/TestClient)
        # We MUST block the current thread until the coro is done.
        # We use a thread-safe way to run the coro and a threading event to wait.
        import threading

        res = []
        err = []
        event = threading.Event()

        async def _wrapper():
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

        res = []
        err = []
        event = threading.Event()

        async def _wrapper():
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
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# ─── FastAPI Dependencies ─────────────────────────────────────────────


async def require_auth(
    request: Request,
    authorization: str | None = Header(None, description="Bearer <api-key>"),
) -> AuthResult:
    """Extract and validate API key from Authorization header with i18n support."""
    from cortex.i18n import get_trans

    lang = request.headers.get("Accept-Language", "en")

    if not authorization:
        raise HTTPException(status_code=401, detail=get_trans("error_missing_auth", lang))

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail=get_trans("error_invalid_key_format", lang))

    manager = get_auth_manager()
    result = await manager.authenticate_async(parts[1])
    if not result.authenticated:
        error_msg = get_trans("error_invalid_revoked_key", lang) if result.error else result.error
        raise HTTPException(status_code=401, detail=error_msg)
    return result


def require_permission(permission: str | Permission):
    """Factory for permission-checking dependencies.

    Supports both legacy string permissions and CORTEX v6 Permission enums.
    """

    async def checker(request: Request, auth: AuthResult = Depends(require_auth)) -> AuthResult:
        # Check against string permissions (v5) OR use RBAC evaluator (v6)
        has_perm = False
        if isinstance(permission, str) and permission in auth.permissions:
            has_perm = True
        elif isinstance(permission, Permission):
            has_perm = RBAC.has_permission(auth.role, permission)

        # Also check if the permission string is in the list
        if not has_perm and str(permission) in auth.permissions:
            has_perm = True

        if not has_perm:
            from cortex.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            perm_name = permission.name if isinstance(permission, Permission) else permission
            detail = get_trans("error_missing_permission", lang).format(permission=perm_name)
            raise HTTPException(status_code=403, detail=detail)
        return auth

    return checker


async def require_consensus(
    claim: str,
    min_score: float = 1.6,
    engine: Any = Depends(lambda: None),  # Placeholder, will be injected
) -> bool:
    """Dependency that verifies a claim has reached sufficient consensus in CORTEX.

    Used for 'Sovereign Gate' high-stakes authorizations.
    """
    if engine is None:
        from cortex.api_deps import get_async_engine

        # Manual resolution if not injected
        async for e in get_async_engine():
            engine = e
            break

    # Look for the claim in memory
    facts = await engine.recall(query=claim, limit=1)
    if not facts:
        return False

    fact = facts[0]
    score = fact.get("consensus_score", 0.0)

    if score < min_score:
        logger.warning(
            "Sovereign Gate: Claim '%s' failed consensus (score: %.2f < %.2f)",
            claim,
            score,
            min_score,
        )
        return False

    return True


def require_verified_permission(permission: str, min_consensus: float = 1.6):
    """Sovereign Gate: Requires both a static permission AND a verified claim.

    Example: require_verified_permission("system_burn", min_consensus=1.8)
    """

    async def sovereign_checker(
        request: Request,
        auth: AuthResult = Depends(require_auth),
    ) -> AuthResult:
        # 1. Standard RBAC check
        if permission not in auth.permissions:
            from cortex.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            detail = get_trans("error_missing_permission", lang).format(permission=permission)
            raise HTTPException(status_code=403, detail=detail)

        # 2. Consensus check (The Sovereign Gate)
        # For now, it checks for a fact stating permission granted
        claim = f"Permission {permission} granted to {auth.key_name or auth.tenant_id}"

        from cortex.api_deps import get_async_engine

        async for engine in get_async_engine():
            has_consensus = await require_consensus(claim, min_score=min_consensus, engine=engine)
            if not has_consensus:
                detail = f"Sovereign Gate: Action requires consensus (min: {min_consensus})"
                raise HTTPException(status_code=403, detail=detail)
            break

        return auth

    return sovereign_checker
