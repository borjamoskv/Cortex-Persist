"""CORTEX Gateway — Universal Intelligence Entry Point.

The Gateway is the unified ingress layer for all external systems
that want to interact with CORTEX's intelligence core.

Architecture::

    External Systems          Gateway              Intelligence Core
    ─────────────────         ───────────          ─────────────────
    REST Clients     ──────→  GatewayRouter   →   CortexEngine
    MCP Tools        ──────→  GatewayRouter   →   EpisodicMemory
    Telegram Bot     ──────→  GatewayRouter   →   Byzantine Consensus
    WebSocket        ──────→  GatewayRouter   →   MEJORAlo / X-Ray
    OpenClaw         ──────→  GatewayRouter   →   NotificationBus

Every request through the Gateway:
1. Is validated (auth, rate limit, size — reusing existing middleware)
2. Is routed to the correct intelligence handler
3. Returns a structured GatewayResponse
4. Optionally triggers a CortexEvent via NotificationBus

Usage::

    from cortex.gateway import GatewayRouter, GatewayRequest

    router = GatewayRouter(engine=engine, bus=notification_bus)
    response = await router.handle(GatewayRequest(
        intent="store",
        project="cortex",
        payload={"content": "Byzantine consensus is working", "type": "decision"},
        source="telegram",
    ))
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.gateway")


# ─── Request / Response Models ────────────────────────────────────────


class GatewayIntent(str, Enum):
    """Supported intents the Gateway can route."""

    STORE = "store"  # Store a fact in memory
    SEARCH = "search"  # Semantic/hybrid search
    RECALL = "recall"  # Recall facts for a project
    STATUS = "status"  # System status
    EMIT = "emit"  # Fire a notification event
    MISSION = "mission"  # Launch a swarm mission
    ASK = "ask"  # Ask the AI (LLM pass-through with memory context)
    MEJORALO = "mejoralo"  # Trigger a MEJORAlo scan


@dataclass
class GatewayRequest:
    """A normalized request to the CORTEX intelligence core.

    Adapters (Telegram, REST, MCP, WebSocket) all produce GatewayRequests.
    This normalization means the intelligence layer never knows which
    channel the request came from.

    Args:
        intent:   What the caller wants to do (see GatewayIntent).
        payload:  Intent-specific data (e.g. {"content": "...", "type": "decision"}).
        project:  Optional project context.
        tenant_id: Optional tenant for federated mode.
        source:   Which adapter generated this request (for logging/audit).
        caller_id: Opaque caller identity (API key ID, chat_id, etc.).
        request_id: Monotonic ID for tracing (auto-generated).
    """

    intent: GatewayIntent
    payload: dict[str, Any] = field(default_factory=dict)
    project: str = ""
    tenant_id: str = "default"
    source: str = "api"
    caller_id: str = ""
    request_id: str = field(default_factory=lambda: f"gw-{int(time.time() * 1000)}")


@dataclass
class GatewayResponse:
    """Structured response from the Gateway.

    Args:
        ok:        Whether the request succeeded.
        data:      Result payload (search results, stored ID, etc.).
        error:     Human-readable error message if ok=False.
        intent:    Echo of the original intent.
        request_id: Echo of the original request_id for correlation.
        latency_ms: Elapsed time in milliseconds.
    """

    ok: bool
    data: Any = None
    error: str = ""
    intent: GatewayIntent = GatewayIntent.STATUS
    request_id: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "intent": self.intent.value,
            "request_id": self.request_id,
            "latency_ms": round(self.latency_ms, 2),
        }


# ─── Gateway Router ──────────────────────────────────────────────────


class GatewayRouter:
    """Routes GatewayRequests to the appropriate CORTEX intelligence handler.

    This is the nerve center: adapters (Telegram, REST, MCP) call
    ``handle()`` and receive a ``GatewayResponse``. The router owns
    no state of its own — it delegates to the engine and bus passed
    at construction time.

    Example::

        router = GatewayRouter(engine=engine, bus=notification_bus)
        resp = await router.handle(GatewayRequest(
            intent=GatewayIntent.SEARCH,
            payload={"query": "Byzantine consensus"},
            project="cortex",
        ))
        print(resp.data)  # list of search results
    """

    def __init__(self, engine: Any, bus: Any = None) -> None:
        """
        Args:
            engine: A CortexEngine (or AsyncCortexEngine) instance.
            bus:    Optional NotificationBus for event delivery.
        """
        self._engine = engine
        self._bus = bus
        self._handlers: dict[GatewayIntent, Any] = {
            GatewayIntent.STORE: self._handle_store,
            GatewayIntent.SEARCH: self._handle_search,
            GatewayIntent.RECALL: self._handle_recall,
            GatewayIntent.STATUS: self._handle_status,
            GatewayIntent.EMIT: self._handle_emit,
        }

    async def handle(self, request: GatewayRequest) -> GatewayResponse:
        """Route request to the correct intelligence handler.

        Always returns a GatewayResponse — never raises.
        """
        t0 = time.perf_counter()
        handler = self._handlers.get(request.intent)

        if handler is None:
            return GatewayResponse(
                ok=False,
                error=f"Unknown intent: {request.intent.value}",
                intent=request.intent,
                request_id=request.request_id,
                latency_ms=0.0,
            )

        try:
            data = await handler(request)
            latency = (time.perf_counter() - t0) * 1000
            logger.info(
                "Gateway [%s] %s → ok (%.1fms) src=%s",
                request.request_id,
                request.intent.value,
                latency,
                request.source,
            )
            return GatewayResponse(
                ok=True,
                data=data,
                intent=request.intent,
                request_id=request.request_id,
                latency_ms=latency,
            )
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - t0) * 1000
            logger.error(
                "Gateway [%s] %s → error: %s",
                request.request_id,
                request.intent.value,
                exc,
                exc_info=True,
            )
            return GatewayResponse(
                ok=False,
                error=str(exc),
                intent=request.intent,
                request_id=request.request_id,
                latency_ms=latency,
            )

    # ─── Intent Handlers ─────────────────────────────────────────────

    async def _handle_store(self, req: GatewayRequest) -> dict[str, Any]:
        content = req.payload.get("content", "")
        fact_type = req.payload.get("type", "knowledge")
        tags = req.payload.get("tags", [])
        source = req.payload.get("source", req.source)

        if not content:
            raise ValueError("payload.content is required for store intent")

        fact_id = await self._engine.store(
            req.project or "default",
            content,
            fact_type,
            tags,
            "stated",
            source,
        )
        return {"fact_id": fact_id, "project": req.project}

    async def _handle_search(self, req: GatewayRequest) -> list[dict]:
        query = req.payload.get("query", "")
        top_k = int(req.payload.get("top_k", 5))

        if not query:
            raise ValueError("payload.query is required for search intent")

        results = await self._engine.search(
            query,
            req.project or None,
            min(max(top_k, 1), 20),
        )
        return [
            {
                "fact_id": r.fact_id,
                "content": r.content,
                "score": round(r.score, 4),
                "project": r.project,
                "type": r.fact_type,
            }
            for r in results
        ]

    async def _handle_recall(self, req: GatewayRequest) -> list[dict]:
        project = req.project or req.payload.get("project", "")
        if not project:
            raise ValueError("project is required for recall intent")

        results = await self._engine.recall(project)
        return [
            {"fact_id": getattr(r, "fact_id", None), "content": getattr(r, "content", str(r))}
            for r in results
        ]

    async def _handle_status(self, req: GatewayRequest) -> dict[str, Any]:
        stats = await self._engine.stats()
        return {
            "status": "operational",
            "total_facts": stats.get("total_facts", 0),
            "active_facts": stats.get("active_facts", 0),
            "projects": stats.get("project_count", 0),
            "db_size_mb": stats.get("db_size_mb", 0),
            "source": req.source,
        }

    async def _handle_emit(self, req: GatewayRequest) -> dict[str, Any]:
        """Fire a CortexEvent through the NotificationBus."""
        if not self._bus:
            return {"delivered": False, "reason": "no notification bus configured"}

        from cortex.notifications.events import CortexEvent, EventSeverity

        severity_str = req.payload.get("severity", "info")
        try:
            severity = EventSeverity(severity_str)
        except ValueError:
            severity = EventSeverity.INFO

        event = CortexEvent(
            severity=severity,
            title=req.payload.get("title", "CORTEX Event"),
            body=req.payload.get("body", ""),
            source=req.source,
            project=req.project,
            metadata=req.payload.get("metadata", {}),
        )
        await self._bus.emit(event)
        return {"delivered": True, "adapters": self._bus.adapter_names}
