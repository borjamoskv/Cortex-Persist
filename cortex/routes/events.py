"""
CORTEX v6.0 - Event Bus Adapter (SSE).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sse_starlette.sse import EventSourceResponse

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.auth.stream import (
    STREAM_COOKIE_MAX_AGE,
    authenticate_stream_key,
    clear_stream_session_cookie,
    issue_stream_session_cookie,
    require_stream_permission,
)
from cortex.engine import CortexEngine as AsyncCortexEngine

__all__ = ["events_router"]

events_router = APIRouter(tags=["events"])
logger = logging.getLogger("cortex.routes.events")


def _serialize_signal(sig: object) -> str:
    """Serialize dataclass-like signal objects without assuming Pydantic helpers."""
    created_at = getattr(sig, "created_at", None)
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    payload = {
        "id": sig.id,
        "event_type": sig.event_type,
        "payload": getattr(sig, "payload", {}),
        "source": getattr(sig, "source", ""),
        "project": getattr(sig, "project", None),
        "created_at": created_at,
        "consumed_by": list(getattr(sig, "consumed_by", [])),
    }
    return json.dumps(payload, default=str)


async def event_generator(
    request: Request,
    engine: AsyncCortexEngine,
    tenant_id: str,
    event_types: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """Generator for Server-Sent Events."""
    bus = getattr(engine, "_signal_bus", None)
    if not bus:
        yield {"event": "error", "data": "Signal Bus not configured"}
        return

    consumer_id = f"sse_{id(request)}"

    try:
        while True:
            if await request.is_disconnected():
                break

            try:
                signals = await bus.poll(
                    tenant_id=tenant_id,
                    consumer=consumer_id,
                    limit=50,
                )
                for sig in signals:
                    if event_types and sig.event_type not in event_types:
                        continue

                    yield {
                        "event": sig.event_type,
                        "id": str(sig.id),
                        "data": _serialize_signal(sig),
                    }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to emit SSE signals: %s", exc)

            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass


@events_router.get("/v1/events/stream")
async def stream_events(
    request: Request,
    types: str | None = Query(None, description="Comma-separated list of event types"),
    auth: AuthResult = Depends(require_stream_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> EventSourceResponse:
    """Subscribe to CORTEX coordination events via SSE."""
    event_types = types.split(",") if types else None
    return EventSourceResponse(event_generator(request, engine, auth.tenant_id, event_types))


@events_router.post("/v1/events/session")
async def create_stream_session(
    request: Request,
    response: Response,
    authorization: str | None = Header(None, description="Bearer <api-key>"),
) -> dict[str, object]:
    """Bootstrap a short-lived HttpOnly cookie for EventSource clients."""
    auth, raw_key = await authenticate_stream_key(request, authorization)
    issue_stream_session_cookie(
        response,
        raw_key,
        auth,
        secure=request.url.scheme == "https",
    )
    return {
        "ok": True,
        "tenant_id": auth.tenant_id,
        "expires_in": STREAM_COOKIE_MAX_AGE,
    }


@events_router.delete("/v1/events/session", status_code=status.HTTP_204_NO_CONTENT)
async def destroy_stream_session(response: Response) -> Response:
    """Clear the EventSource session cookie."""
    clear_stream_session_cookie(response)
    return response
