"""
CORTEX v5.0 — Authentication & Authorization.

API key management with SHA-256 hashing. Keys are stored hashed,
never in plaintext. Supports scoped permissions per tenant.
"""

import hashlib
import json
import logging
import secrets
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, Request

__all__ = [
    "APIKey",
    "AUTH_SCHEMA",
    "AuthManager",
    "AuthResult",
    "SQL_INSERT_KEY",
    "get_auth_manager",
    "require_auth",
    "require_permission",
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
    INSERT INTO api_keys (name, key_hash, key_prefix, tenant_id, permissions, rate_limit)
    VALUES (?, ?, ?, ?, ?, ?)
"""


@dataclass
class APIKey:
    """Represents an API key with its metadata."""

    id: int
    name: str
    key_prefix: str
    tenant_id: str
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
    permissions: list[str] = field(default_factory=list)
    key_name: str = ""
    error: str = ""


class AuthManager:
    """Manages API key authentication for CORTEX."""

    KEY_LENGTH = 32  # 256-bit keys

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        from cortex.db import connect

        return connect(self.db_path, row_factory=sqlite3.Row)

    def _init_schema(self) -> None:
        conn = self._get_conn()
        try:
            conn.executescript(AUTH_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def create_key(
        self,
        name: str,
        tenant_id: str = "default",
        permissions: list[str] | None = None,
        rate_limit: int = 100,
    ) -> tuple[str, APIKey]:
        """Create a new API key. Returns (raw_key, APIKey metadata).

        The raw key is shown only once — store it securely.
        """
        if permissions is None:
            permissions = ["read", "write"]

        raw_key = f"ctx_{secrets.token_hex(self.KEY_LENGTH)}"
        key_hash = self._hash_key(raw_key)
        key_prefix = raw_key[:12]

        args = (name, key_hash, key_prefix, tenant_id, json.dumps(permissions), rate_limit)
        conn = self._get_conn()
        try:
            cursor = conn.execute(SQL_INSERT_KEY, args)
            conn.commit()
            key_id = cursor.lastrowid

            new_api_key = APIKey(
                id=key_id,
                name=name,
                key_prefix=key_prefix,
                tenant_id=tenant_id,
                permissions=permissions,
                created_at=datetime.now(timezone.utc).isoformat(),
                last_used=None,
                is_active=True,
                rate_limit=rate_limit,
            )
            logger.info("Created API key '%s' for tenant '%s'", name, tenant_id)
            return raw_key, new_api_key
        finally:
            conn.close()

    @lru_cache(maxsize=1024)  # noqa: B019
    def authenticate(self, raw_key: str) -> AuthResult:
        """Authenticate a request using an API key (Cached)."""
        is_valid_format = bool(raw_key and raw_key.startswith("ctx_"))

        # Finding 4: Always compute a hash to waste CPU time even if format is invalid.
        # This mitigates early-exit timing leaks.
        dummy_hash = self._hash_key("ctx_invalid_dummy_key_to_waste_time")
        key_hash = self._hash_key(raw_key) if is_valid_format else dummy_hash

        if not is_valid_format:
            return AuthResult(authenticated=False, error="Invalid key format")

        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
                (key_hash,),
            ).fetchone()

            if not row:
                return AuthResult(authenticated=False, error="Invalid or revoked key")

            self._update_last_used(conn, row["id"])

            return AuthResult(
                authenticated=True,
                tenant_id=row["tenant_id"],
                permissions=json.loads(row["permissions"]),
                key_name=row["name"],
            )
        finally:
            conn.close()

    def _update_last_used(self, conn: sqlite3.Connection, key_id: int) -> None:
        """Update last_used timestamp (best-effort)."""
        try:
            conn.execute(
                "UPDATE api_keys SET last_used = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), key_id),
            )
            conn.commit()
        except sqlite3.OperationalError:
            logger.debug("Could not update last_used (DB busy), skipping")

    def revoke_key(self, key_id: int) -> bool:
        """Revoke an API key by ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_keys(self, tenant_id: str | None = None) -> list[APIKey]:
        """List all API keys, optionally filtered by tenant."""
        conn = self._get_conn()
        try:
            if tenant_id:
                rows = conn.execute(
                    "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC").fetchall()

            return [
                APIKey(
                    id=r["id"],
                    name=r["name"],
                    key_prefix=r["key_prefix"],
                    tenant_id=r["tenant_id"],
                    permissions=json.loads(r["permissions"]),
                    created_at=r["created_at"],
                    last_used=r["last_used"],
                    is_active=bool(r["is_active"]),
                    rate_limit=r["rate_limit"],
                )
                for r in rows
            ]
        finally:
            conn.close()


# ─── Singleton ────────────────────────────────────────────────────────

_auth_manager: AuthManager | None = None


def get_auth_manager() -> AuthManager:
    """Lazy-load the global AuthManager instance."""
    from cortex.config import DB_PATH

    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(DB_PATH)
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
    result = manager.authenticate(parts[1])
    if not result.authenticated:
        error_msg = get_trans("error_invalid_revoked_key", lang) if result.error else result.error
        raise HTTPException(status_code=401, detail=error_msg)
    return result


def require_permission(permission: str):
    """Factory for permission-checking dependencies with i18n support."""

    async def checker(request: Request, auth: AuthResult = Depends(require_auth)) -> AuthResult:
        if permission not in auth.permissions:
            from cortex.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            detail = get_trans("error_missing_permission", lang).format(permission=permission)
            raise HTTPException(status_code=403, detail=detail)
        return auth

    return checker
