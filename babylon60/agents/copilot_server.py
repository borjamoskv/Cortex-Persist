# [C5-REAL] Exergy-Maximized
"""CORTEX Level 3 Copilot - WebSocket Server.

Bridges IDE clients (VS Code extension) to the CopilotAgent backend.

Architecture:
    [VS Code Extension] ←WebSocket→ [CopilotServer] ←MessageBus→ [CopilotAgent]

Protocol:
    Client → Server: {"type": "context", "payload": CopilotContextPayload}
    Server → Client: {"type": "suggestions", "payload": SuggestionBatch}
    Client → Server: {"type": "verdict", "payload": SuggestionVerdict}
    Server → Client: {"type": "telemetry", "payload": CopilotTelemetry}
    Server → Client: {"type": "error", "message": str}
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import uuid4

from babylon60.agents.builtins.copilot_agent import CopilotAgent, create_copilot_agent
from babylon60.agents.copilot_contracts import (
    CopilotContextPayload,
    SuggestionVerdict,
)
from babylon60.agents.message_schema import MessageKind, new_message
from babylon60.guards import AntiLimerenceGuard

logger = logging.getLogger("babylon60.agents.copilot.server")

try:
    import websockets  # noqa: F401
    from websockets.asyncio.server import serve as ws_serve

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    logger.debug("websockets not installed - CopilotServer unavailable")


# ── Session Tracking ──────────────────────────────────────────────


class _ClientSession:
    """Tracks a connected IDE client."""

    __slots__ = (
        "connected_at",
        "messages_received",
        "messages_sent",
        "session_id",
        "websocket",
        "limerence_guard",
    )

    def __init__(self, websocket: Any) -> None:
        self.session_id = f"session-{uuid4().hex[:8]}"
        self.websocket = websocket
        self.connected_at = time.monotonic()
        self.messages_received = 0
        self.messages_sent = 0
        self.limerence_guard = AntiLimerenceGuard()


# ── In-Memory Bus for Server ─────────────────────────────────────


class _ServerBus:
    """Lightweight in-process message bus for the copilot server.

    Routes messages between the WebSocket handler and the CopilotAgent.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    async def send(self, msg: Any) -> None:
        q = self._queues.setdefault(msg.recipient, asyncio.Queue())
        await q.put(msg)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> Any | None:
        q = self._queues.setdefault(agent_id, asyncio.Queue())
        try:
            return await asyncio.wait_for(q.get(), timeout=timeout)
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None


# ── Copilot Server ────────────────────────────────────────────────


class CopilotServer:
    """WebSocket server that bridges IDE clients to CopilotAgent.

    Manages multiple concurrent IDE sessions.
    Each client gets its own session but shares the same CopilotAgent.

    Usage:
        server = CopilotServer(agent)
        await server.start()
    """

    def __init__(
        self,
        agent: CopilotAgent,
        *,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        if not HAS_WEBSOCKETS:
            raise ImportError("websockets library required: pip install websockets")

        self._agent = agent
        self._host = host
        self._port = port
        self._sessions: dict[str, _ClientSession] = {}
        self._server: Any = None
        self._running = False

    @property
    def session_count(self) -> int:
        """Number of active client sessions."""
        return len(self._sessions)

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._running = True
        self._server = await ws_serve(
            self._handle_connection,
            self._host,
            self._port,
        )
        logger.info(
            "CopilotServer listening on ws://%s:%d",
            self._host,
            self._port,
        )

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("CopilotServer stopped (%d sessions were active)", len(self._sessions))
        self._sessions.clear()

    async def _handle_connection(self, websocket: Any) -> None:
        """Handle a new client connection."""
        session = _ClientSession(websocket)
        self._sessions[session.session_id] = session
        logger.info("Client connected: %s", session.session_id)

        try:
            async for raw_message in websocket:
                await self._handle_message(session, raw_message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Client %s error: %s", session.session_id, exc)
        finally:
            del self._sessions[session.session_id]
            logger.info(
                "Client disconnected: %s (msgs_in=%d, msgs_out=%d)",
                session.session_id,
                session.messages_received,
                session.messages_sent,
            )

    async def _handle_message(
        self,
        session: _ClientSession,
        raw: str,
    ) -> None:
        """Route an incoming JSON message."""
        session.messages_received += 1

        try:
            session.limerence_guard.check_iteration(raw, agent_id=session.session_id)
        except RuntimeError as exc:
            await self._send_error(session, str(exc))
            await session.websocket.close(1008, "Limerence Kill Criteria Triggered")
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            await self._send_error(session, f"Invalid JSON: {exc}")
            return

        msg_type = data.get("type")
        payload = data.get("payload", {})

        if msg_type == "context":
            await self._handle_context(session, payload)
        elif msg_type == "verdict":
            await self._handle_verdict(session, payload)
        elif msg_type == "telemetry":
            await self._send_telemetry(session)
        elif msg_type == "health":
            await self._send_json(session, {"type": "health", "status": "ok"})
        else:
            await self._send_error(session, f"Unknown message type: {msg_type}")

    async def _handle_context(
        self,
        session: _ClientSession,
        payload: dict[str, Any],
    ) -> None:
        """Process context → generate suggestions → send back."""
        try:
            context = CopilotContextPayload(**payload)
        except (ValueError, TypeError, OSError, KeyError) as exc:
            await self._send_error(session, f"Invalid context: {exc}")
            return

        # Route to CopilotAgent via internal message
        sender_id = f"ws-{session.session_id}"

        msg = new_message(
            sender=sender_id,
            recipient=self._agent.agent_id,
            kind=MessageKind.TASK_REQUEST,
            payload=context.model_dump(mode="json"),
        )
        await self._agent.handle_message(msg)

        # Get the response from the bus
        response = await self._agent.bus.receive(sender_id, timeout=10.0)

        if response and response.payload:
            await self._send_json(
                session,
                {
                    "type": "suggestions",
                    "payload": response.payload,
                },
            )
        else:
            await self._send_error(session, "No suggestions generated")

    async def _handle_verdict(
        self,
        session: _ClientSession,
        payload: dict[str, Any],
    ) -> None:
        """Process human verdict on a suggestion."""
        try:
            verdict = SuggestionVerdict(**payload)
        except (ValueError, TypeError, OSError, KeyError) as exc:
            await self._send_error(session, f"Invalid verdict: {exc}")
            return

        sender_id = f"ws-{session.session_id}"

        msg = new_message(
            sender=sender_id,
            recipient=self._agent.agent_id,
            kind=MessageKind.TASK_RESULT,
            payload=verdict.model_dump(mode="json"),
        )
        await self._agent.handle_message(msg)

        # Send updated telemetry after verdict
        await self._send_telemetry(session)

    async def _send_telemetry(self, session: _ClientSession) -> None:
        """Send current telemetry to client."""
        await self._send_json(
            session,
            {
                "type": "telemetry",
                "payload": self._agent.get_telemetry(),
            },
        )

    async def _send_error(self, session: _ClientSession, message: str) -> None:
        """Send an error message to client."""
        await self._send_json(session, {"type": "error", "message": message})

    async def _send_json(self, session: _ClientSession, data: dict[str, Any]) -> None:
        """Send JSON to a client session."""
        try:
            await session.websocket.send(json.dumps(data))
            session.messages_sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Send to %s failed: %s", session.session_id, exc)


# ── Factory ───────────────────────────────────────────────────────


def create_copilot_server(
    *,
    host: str = "localhost",
    port: int = 8765,
    model: str = "gemini-2.5-pro",
) -> tuple[CopilotServer, CopilotAgent]:
    """Factory: create a CopilotServer with a new CopilotAgent.

    Returns:
        (server, agent) tuple for lifecycle management.
    """
    bus = _ServerBus()
    agent = create_copilot_agent(bus, agent_id="copilot-ws", model=model)
    server = CopilotServer(agent, host=host, port=port)
    return server, agent
