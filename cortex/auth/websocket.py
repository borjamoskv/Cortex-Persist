"""Shared authentication helpers for WebSocket routes."""

from __future__ import annotations

from fastapi import WebSocket

from cortex.auth.manager import get_auth_manager
from cortex.auth.models import AuthResult
from cortex.extensions.security.tenant import tenant_id_var

__all__ = ["require_websocket_auth"]


async def require_websocket_auth(
    websocket: WebSocket, required_permission: str = "read"
) -> AuthResult | None:
    """Authenticate a WebSocket before accepting the connection.

    Supports both `Authorization: Bearer <key>` and `?api_key=...` for browser
    clients that cannot set custom headers in the native WebSocket handshake.
    """
    raw_key = ""
    authorization = websocket.headers.get("authorization", "")
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_key = parts[1].strip()
    if not raw_key:
        raw_key = websocket.query_params.get("api_key", "").strip()
    if not raw_key:
        await websocket.close(code=4401, reason="Missing API key")
        return None

    manager = getattr(websocket.app.state, "auth_manager", None) or get_auth_manager()
    if manager is None:
        await websocket.close(code=1011, reason="Auth manager unavailable")
        return None

    auth = await manager.authenticate_async(raw_key)
    if not auth.authenticated:
        await websocket.close(code=4401, reason="Invalid API key")
        return None
    if required_permission not in auth.permissions:
        await websocket.close(code=4403, reason="Missing permission")
        return None

    tenant_id_var.set(auth.tenant_id)
    return auth
