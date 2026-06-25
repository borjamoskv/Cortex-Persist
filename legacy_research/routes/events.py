# [C5-REAL] Exergy-Maximized
"""
Event Bus Adapter (SSE).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Query, Request
from sse_starlette.sse import EventSourceResponse

from cortex.api.deps import get_async_engine
from legacy_research.auth import AuthResult, require_permission
from cortex.engine import CortexEngine as AsyncCortexEngine

__all__ = ["events_router"]

events_router = APIRouter(tags=["events"])


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
                signals = await bus.poll(consumer=consumer_id, limit=50)
                for sig in signals:
                    if event_types and sig.event_type not in event_types:
                        continue

                    yield {
                        "event": sig.event_type,
                        "id": str(sig.id),
                        "data": sig.model_dump_json()
                        if hasattr(sig, "model_dump_json")
                        else sig.json(),
                    }
            except Exception as exc:
                import logging

                logging.warning("Suppressed exception: %s", exc)

            await asyncio.sleep(1.0)
    except Exception as exc:
        import logging

        logging.warning("Suppressed exception: %s", exc)


@events_router.get("/v1/events/stream")
async def stream_events(
    request: Request,
    types: str | None = Query(None, description="Comma-separated list of event types"),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> EventSourceResponse:
    """Subscribe to CORTEX coordination events via SSE."""
    event_types = types.split(",") if types else None
    return EventSourceResponse(event_generator(request, engine, auth.tenant_id, event_types))
