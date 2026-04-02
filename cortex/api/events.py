import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

import cortex.api.state as api_state
from cortex.extensions.signals.bus import AsyncSignalBus

router = APIRouter(prefix="/v1/events", tags=["events"])
logger = logging.getLogger("cortex.api.events")


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    """Polls AsyncSignalBus and yields SSE events to the client."""
    # Get the shared database pool from app state
    pool = getattr(request.app.state, "pool", None)
    if not pool:
        logger.error("SSE: No database pool found in app state.")
        yield "data: {\"error\": \"Database pool not available\"}\n\n"
        return

    # Use the pool to get a connection and initialize the bus
    async with pool.acquire() as conn:
        bus = AsyncSignalBus(conn)
        consumer_id = f"sse_{id(request)}"
        
        logger.info("SSE: Client connected: %s", consumer_id)
        
        try:
            while True:
                # Check for disconnection
                if await request.is_disconnected():
                    logger.info("SSE: Client disconnected: %s", consumer_id)
                    break
                
                # Poll for new signals
                signals = await bus.poll(consumer=consumer_id, limit=10)
                
                for sig in signals:
                    # Construct SSE message
                    event_data = {
                        "id": sig.id,
                        "event_type": sig.event_type,
                        "payload": sig.payload,
                        "source": sig.source,
                        "created_at": sig.created_at
                    }
                    yield f"event: {sig.event_type}\ndata: {json.dumps(event_data)}\n\n"
                
                # 1-second pulse interval for O(1) efficiency
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("SSE: Stream cancelled for %s", consumer_id)
        except Exception as e:
            logger.error("SSE: Stream error: %s", e)
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"


@router.get("/stream")
async def stream_events(request: Request):
    """Server-Sent Events endpoint for real-time CORTEX telemetry."""
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream"
    )
