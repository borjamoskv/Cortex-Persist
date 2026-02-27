"""
CORTEX v5.0 — Notch WebSocket Hub (Bridge #6 Server-Side).

Bidirectional communication between CORTEX and Notch Live:
- CORTEX → Notch: push commands (thinking, idle, mode:X, model:X, ghost:refresh)
- Notch → CORTEX: heartbeat pongs, status updates

Usage from anywhere in CORTEX:
    from cortex.routes.notch_ws import notch_hub
    await notch_hub.broadcast("thinking")
"""

from __future__ import annotations

import asyncio
import logging
from typing import ClassVar

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

__all__ = ["notch_hub", "router"]

router = APIRouter(tags=["notch"])
logger = logging.getLogger("cortex.notch_ws")


class NotchHub:
    """Manages all connected Notch Live clients.

    Thread-safe singleton — any part of CORTEX can call
    ``await notch_hub.broadcast("thinking")`` to push state to the notch.
    """

    _instance: ClassVar[NotchHub | None] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __new__(cls) -> NotchHub:
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._clients: set[WebSocket] = set()
            cls._instance = inst
        return cls._instance

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        logger.info("Notch client connected (%d total)", self.client_count)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)
        logger.info("Notch client disconnected (%d remaining)", self.client_count)

    async def broadcast(self, message: str) -> None:
        """Send a command to ALL connected notch clients."""
        dead: list[WebSocket] = []
        for ws in self._clients:
            try:
                await ws.send_text(message)
            except (WebSocketDisconnect, RuntimeError, OSError):
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)

    async def send_to_first(self, message: str) -> bool:
        """Send to the first connected client (primary notch). Returns False if none."""
        for ws in self._clients:
            try:
                await ws.send_text(message)
                return True
            except (WebSocketDisconnect, RuntimeError, OSError):
                self._clients.discard(ws)
        return False


# Global singleton — importable from anywhere
notch_hub = NotchHub()


# ── WebSocket Endpoint ──────────────────────────────────────────────


@router.websocket("/ws/notch")
async def notch_websocket(ws: WebSocket) -> None:
    """Bidirectional WebSocket for Notch Live ↔ CORTEX communication.

    Commands CORTEX → Notch:
        "thinking"       → activate chromatic aberration + breathing
        "idle"           → deactivate thinking, return to IDLE
        "mode:ULTRATHINK"→ change displayed mode
        "model:gemini-2.5" → change displayed model
        "ping"           → heartbeat check (expects "pong" back)
        "ghost:refresh"  → trigger Ghost Panel reload

    Messages Notch → CORTEX:
        "pong"           → heartbeat response
        "status:..."     → status update from notch
    """
    await notch_hub.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = data.strip()

            if msg == "pong":
                logger.debug("Heartbeat pong received from notch")
            elif msg.startswith("status:"):
                logger.info("Notch status: %s", msg[7:])
            else:
                logger.debug("Notch message: %s", msg)

    except WebSocketDisconnect:
        pass
    except (OSError, RuntimeError) as exc:
        logger.warning("Notch WS error: %s", exc)
    finally:
        notch_hub.disconnect(ws)


# ── Convenience functions for CORTEX internals ──────────────────────


async def notify_notch_thinking() -> None:
    """Shortcut: tell the notch we're thinking."""
    await notch_hub.broadcast("thinking")


async def notify_notch_idle() -> None:
    """Shortcut: tell the notch we're idle."""
    await notch_hub.broadcast("idle")


async def notify_notch_mode(mode: str) -> None:
    """Shortcut: update the notch mode display."""
    await notch_hub.broadcast(f"mode:{mode}")


async def notify_notch_model(model: str) -> None:
    """Shortcut: update the notch model display."""
    await notch_hub.broadcast(f"model:{model}")


async def notify_notch_pruning() -> None:
    """Shortcut: tell the notch we just pruned/filtered memory (Entropy Shockwave)."""
    await notch_hub.broadcast('{"command": "shockwave", "intensity": 1.0}')
