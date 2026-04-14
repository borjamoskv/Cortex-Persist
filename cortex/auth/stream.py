"""Browser-compatible auth helpers for SSE and other stream-style routes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

from fastapi import Depends, Header, HTTPException, Request, Response

from cortex.auth.manager import get_auth_manager
from cortex.auth.models import AuthResult
from cortex.auth.rbac import Permission, RBAC
from cortex.extensions.security.tenant import tenant_id_var

__all__ = [
    "STREAM_COOKIE_MAX_AGE",
    "STREAM_COOKIE_NAME",
    "authenticate_stream_key",
    "clear_stream_session_cookie",
    "issue_stream_session_cookie",
    "require_stream_auth",
    "require_stream_permission",
]

logger = logging.getLogger(__name__)
STREAM_COOKIE_NAME = "cortex_stream"
STREAM_COOKIE_MAX_AGE = 300
_STREAM_SECRET = (
    os.environ.get("CORTEX_STREAM_SECRET")
    or os.environ.get("CORTEX_GATE_SECRET")
    or os.environ.get("CORTEX_VAULT_KEY")
    or secrets.token_hex(32)
)


def _extract_bearer_token(authorization: str | None) -> str:
    """Extract a raw API key from a standard Bearer header."""
    if not authorization:
        return ""
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ""
    return parts[1].strip()


def _b64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _b64url_decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def _sign_stream_payload(payload_b64: str) -> str:
    return hmac.new(_STREAM_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()


def _mint_stream_token(raw_key: str, auth: AuthResult, *, ttl: int = STREAM_COOKIE_MAX_AGE) -> str:
    """Create a short-lived signed token for SSE cookie auth."""
    payload = {
        "key_hash": hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
        "tenant_id": auth.tenant_id,
        "role": auth.role,
        "permissions": [str(permission) for permission in auth.permissions],
        "exp": int(time.time()) + ttl,
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign_stream_payload(payload_b64)
    return f"{payload_b64}.{signature}"


def _decode_stream_token(token: str) -> dict[str, object]:
    """Verify and decode a signed SSE stream token."""
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid stream session") from exc

    expected_signature = _sign_stream_payload(payload_b64)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid stream session")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid stream session") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=401, detail="Invalid stream session")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at <= int(time.time()):
        raise HTTPException(status_code=401, detail="Expired stream session")

    key_hash = payload.get("key_hash")
    if not isinstance(key_hash, str) or not key_hash:
        raise HTTPException(status_code=401, detail="Invalid stream session")

    return payload


async def _get_stream_auth_from_cookie(request: Request, token: str) -> AuthResult:
    """Resolve a short-lived stream session cookie back to an active API key row."""
    payload = _decode_stream_token(token)
    manager = getattr(request.app.state, "auth_manager", None) or get_auth_manager()
    if manager is None:
        logger.error("Stream cookie auth requested before auth manager was initialized.")
        raise HTTPException(status_code=503, detail="Auth manager unavailable")

    row = await manager.backend.get_key_by_hash(payload["key_hash"])
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or revoked key")

    permissions = row["permissions"]
    if isinstance(permissions, str):
        permissions = json.loads(permissions)

    auth = AuthResult(
        authenticated=True,
        tenant_id=row["tenant_id"],
        role=row["role"] if "role" in row else "user",
        permissions=permissions,
        key_name=row["name"],
    )
    tenant_id_var.set(auth.tenant_id)
    return auth


async def authenticate_stream_key(
    request: Request,
    authorization: str | None = Header(None, description="Bearer <api-key>"),
) -> tuple[AuthResult, str]:
    """Authenticate a raw API key presented in the Authorization header."""
    raw_key = _extract_bearer_token(authorization)
    if not raw_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    manager = getattr(request.app.state, "auth_manager", None) or get_auth_manager()
    if manager is None:
        logger.error("Stream auth requested before auth manager was initialized.")
        raise HTTPException(status_code=503, detail="Auth manager unavailable")

    result = await manager.authenticate_async(raw_key)
    if not result.authenticated:
        raise HTTPException(status_code=401, detail=result.error or "Invalid or revoked key")

    tenant_id_var.set(result.tenant_id)
    return result, raw_key


def issue_stream_session_cookie(
    response: Response,
    raw_key: str,
    auth: AuthResult,
    *,
    secure: bool,
    max_age: int = STREAM_COOKIE_MAX_AGE,
) -> None:
    """Attach a short-lived HttpOnly cookie for SSE authentication."""
    token = _mint_stream_token(raw_key, auth, ttl=max_age)
    response.set_cookie(
        STREAM_COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/v1/events/stream",
    )


def clear_stream_session_cookie(response: Response) -> None:
    """Remove the SSE session cookie."""
    response.delete_cookie(STREAM_COOKIE_NAME, path="/v1/events/stream")


async def require_stream_auth(
    request: Request,
    authorization: str | None = Header(None, description="Bearer <api-key>"),
) -> AuthResult:
    """Authenticate a stream request via header or short-lived HttpOnly cookie."""
    raw_key = _extract_bearer_token(authorization)
    if raw_key:
        auth, _ = await authenticate_stream_key(request, authorization)
        return auth

    cookie_token = request.cookies.get(STREAM_COOKIE_NAME)
    if cookie_token:
        return await _get_stream_auth_from_cookie(request, cookie_token)

    raise HTTPException(status_code=401, detail="Missing API key")


def require_stream_permission(permission: str | Permission):
    """Permission gate for stream routes using browser-compatible auth."""

    async def checker(
        request: Request,
        auth: AuthResult = Depends(require_stream_auth),
    ) -> AuthResult:
        has_perm = False
        if isinstance(permission, str) and permission in auth.permissions:
            has_perm = True
        elif isinstance(permission, Permission):
            has_perm = RBAC.has_permission(auth.role, permission)

        if not has_perm and str(permission) in auth.permissions:
            has_perm = True

        if not has_perm:
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return auth

    return checker
