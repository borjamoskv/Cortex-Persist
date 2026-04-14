import asyncio
import os
import json
import logging
import sys
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn
import aiosqlite

# CORTEX V5 Pulse Integration
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist")
from cortex.config import DB_PATH
from cortex.extensions.signals.bus import AsyncSignalBus

# Logging Configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] CORTEX-SERVER: %(message)s"
)
logger = logging.getLogger("cortex.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_conn = await aiosqlite.connect(DB_PATH)
    logger.info("Sovereign Memory Backend Connected: %s", DB_PATH)
    try:
        yield
    finally:
        await app.state.db_conn.close()


app = FastAPI(title="CORTEX-X100-SSE-ENGINE", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SHARED STATE (Legacy/Hybrid) --- #
STATE = {
    "is_running": False,
    "cycle_count": 0,
    "global_yield": 0.0,
    "exergy_ratio": 1.0,
    "vectors": [
        {"id": "bounty", "name": "Code4rena Bounties", "yield": 0.0, "baseline": 2.5},
        {"id": "mev", "name": "LayerZero Fuzz", "yield": 0.0, "baseline": 1.2},
        {
            "id": "millennium",
            "name": "Riemann Singularities ($1M)",
            "yield": 0.0,
            "baseline": 1000.0,
        },
    ],
    "logs": [],
    "agent_states": [0.0] * 10000,
}


def _signal_payload(sig: object) -> dict[str, object]:
    created_at = getattr(sig, "created_at", None)
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    return {
        "id": getattr(sig, "id"),
        "event_type": getattr(sig, "event_type"),
        "payload": getattr(sig, "payload", {}),
        "source": getattr(sig, "source", ""),
        "created_at": created_at,
    }


def _update_legacy_state(event_data: dict[str, object]) -> None:
    event_type = str(event_data.get("event_type", "signal"))
    payload = event_data.get("payload", {})
    log_entry = {
        "id": time.time(),
        "msg": event_type,
        "val": json.dumps(payload, default=str),
    }
    STATE["logs"].append(log_entry)
    STATE["logs"] = STATE["logs"][-50:]

    if event_type == "ledger_append" and isinstance(payload, dict):
        try:
            STATE["global_yield"] += float(payload.get("yield_amount", 0.0))
        except (TypeError, ValueError):
            pass

    STATE["cycle_count"] += 1


def _legacy_snapshot() -> dict[str, object]:
    return {
        "is_running": STATE["is_running"],
        "cycle_count": STATE["cycle_count"],
        "global_yield": STATE["global_yield"],
        "exergy_ratio": STATE["exergy_ratio"],
        "vectors": STATE["vectors"],
        "logs": STATE["logs"],
        "agent_states": STATE["agent_states"],
    }

# --- V5 SSE TELEMETRY PORT --- #
@app.get("/v1/events/stream")
async def sse_stream(request: Request):
    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        bus = AsyncSignalBus(app.state.db_conn)
        consumer_id = f"dashboard_{uuid.uuid4().hex}"
        logger.info("SSE: New consumer connected: %s", consumer_id)

        try:
            while True:
                if await request.is_disconnected():
                    logger.info("SSE: Consumer disconnected: %s", consumer_id)
                    break

                # Poll for new signals
                signals = await bus.poll(consumer=consumer_id, limit=20)
                for sig in signals:
                    event_data = _signal_payload(sig)
                    _update_legacy_state(event_data)
                    yield {
                        "event": str(sig.event_type),
                        "id": str(sig.id),
                        "data": json.dumps(event_data, default=str),
                    }

                # Legacy dashboards still consume unnamed snapshot events.
                yield {"data": json.dumps(_legacy_snapshot(), default=str)}

                # Keep-alive pulse
                if not signals:
                    yield {"comment": "ping"}

                await asyncio.sleep(1)
        except Exception as e:
            logger.error("SSE Stream Error: %s", e)

    return EventSourceResponse(event_generator())


# --- WEBSOCKET BINARY SWARM VISUALIZER --- #
class SwarmManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_binary(self, data: bytes):
        for connection in self.active_connections:
            try:
                await connection.send_bytes(data)
            except Exception:
                pass


swarm_manager = SwarmManager()


@app.websocket("/ws/swarm")
async def websocket_endpoint(websocket: WebSocket):
    await swarm_manager.connect(websocket)
    try:
        while True:
            # Heartbeat check
            await websocket.receive_text()
    except WebSocketDisconnect:
        swarm_manager.disconnect(websocket)


# --- LEGACY COMPATIBILITY ENDPOINTS --- #
@app.get("/stream")
async def legacy_stream(request: Request):
    """Proxy /stream to /v1/events/stream for older dashboard versions."""
    return await sse_stream(request)


if __name__ == "__main__":
    logger.info("Launching CORTEX Aether Matrix Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
