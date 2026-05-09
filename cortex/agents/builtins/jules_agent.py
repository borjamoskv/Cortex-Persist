"""CORTEX Agent — Jules Bridge Agent.

Bidirectional communication bridge between CORTEX agent bus and Google Jules.
Receives TASK_REQUESTs from internal agents, translates them to Jules sessions,
monitors execution, and routes results back through the bus.

Supported operations:
    - dispatch: Create a Jules session with a prompt + repo context
    - status:   Query an existing session's state
    - message:  Send a follow-up message to an active session
    - approve:  Approve a pending plan
    - list:     List recent Jules sessions
    - activities: Get session activity log
    - poll:     Wait for session completion (blocking)
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.gateway.jules import JulesClient, source_from_repo

logger = logging.getLogger("cortex.agents.jules")

_SUPPORTED_OPS: frozenset[str] = frozenset(
    {"dispatch", "status", "message", "approve", "list", "activities", "poll"}
)

# Default CORTEX-Persist repo context
DEFAULT_OWNER = "borjamoskv"
DEFAULT_REPO = "Cortex-Persist"


class JulesAgent(BaseAgent):
    """Reactive agent — bridges CORTEX bus to Jules API.

    Translates internal TASK_REQUESTs into Jules sessions and routes
    results back. Maintains a JulesClient for the session lifecycle.

    Expects JULES_API_KEY environment variable or api_key in constructor.
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        *,
        api_key: str | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._api_key = api_key
        self._client: JulesClient | None = None
        # Track dispatched sessions for correlation
        self._active_sessions: dict[str, str] = {}  # session_id → correlation_id

    async def on_start(self) -> None:
        """Initialize Jules client on agent start."""
        self._client = JulesClient(api_key=self._api_key)
        await self._client.__aenter__()
        logger.info("[%s] Jules client initialized", self.agent_id)

    async def on_stop(self) -> None:
        """Cleanup Jules client on agent stop."""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
        logger.info("[%s] Jules client closed", self.agent_id)

    # ── Message handler ──────────────────────────────────────

    async def handle_message(self, message: AgentMessage) -> None:
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        op: str = payload.get("op", "")

        if op not in _SUPPORTED_OPS:
            await self._reply(
                message,
                {"error": f"unsupported op: {op!r}", "supported": sorted(_SUPPORTED_OPS)},
            )
            return

        if not self._client:
            await self._reply(message, {"error": "Jules client not initialized"})
            return

        try:
            result = await self._dispatch_op(op, payload)
            await self._reply(message, {"op": op, "result": result})
        except Exception as exc:
            logger.exception("JulesAgent op=%s failed", op)
            await self._reply(message, {"op": op, "error": str(exc)})

    async def tick(self) -> None:
        """Idle tick — could be extended for session polling daemon mode."""

    # ── Operation dispatch ───────────────────────────────────

    async def _dispatch_op(self, op: str, payload: dict[str, Any]) -> Any:
        assert self._client is not None  # noqa: S101

        if op == "dispatch":
            return await self._op_dispatch(payload)
        if op == "status":
            return await self._op_status(payload)
        if op == "message":
            return await self._op_message(payload)
        if op == "approve":
            return await self._op_approve(payload)
        if op == "list":
            return await self._op_list(payload)
        if op == "activities":
            return await self._op_activities(payload)
        if op == "poll":
            return await self._op_poll(payload)

        raise ValueError(f"unknown op: {op!r}")

    async def _op_dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new Jules session from a CORTEX task."""
        assert self._client is not None  # noqa: S101

        prompt = payload.get("prompt", "")
        if not prompt:
            raise ValueError("'prompt' is required for dispatch op")

        owner = payload.get("owner", DEFAULT_OWNER)
        repo = payload.get("repo", DEFAULT_REPO)
        branch = payload.get("branch", "main")
        title = payload.get("title")
        require_approval = payload.get("require_plan_approval", True)

        source = source_from_repo(owner, repo)

        session = await self._client.create_session(
            prompt=prompt,
            source=source,
            branch=branch,
            title=title,
            require_plan_approval=require_approval,
        )

        # Extract session ID from name (format: "sessions/{id}")
        session_name = session.get("name", "")
        session_id = session_name.rsplit("/", 1)[-1] if "/" in session_name else session_name

        logger.info(
            "[%s] Dispatched to Jules: session=%s, prompt=%.80s",
            self.agent_id, session_id, prompt,
        )

        return {
            "session_id": session_id,
            "session_name": session_name,
            "state": session.get("state", "UNKNOWN"),
            "web_url": f"https://jules.google.com/session/{session_id}",
        }

    async def _op_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Get status of an existing Jules session."""
        assert self._client is not None  # noqa: S101

        session_id = payload.get("session_id", "")
        if not session_id:
            raise ValueError("'session_id' is required for status op")

        session = await self._client.get_session(session_id)
        return {
            "session_id": session_id,
            "state": session.get("state", "UNKNOWN"),
            "title": session.get("title", ""),
            "raw": session,
        }

    async def _op_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a message to an active Jules session."""
        assert self._client is not None  # noqa: S101

        session_id = payload.get("session_id", "")
        message_text = payload.get("message", "")
        if not session_id or not message_text:
            raise ValueError("'session_id' and 'message' required for message op")

        result = await self._client.send_message(session_id, message_text)
        return {"session_id": session_id, "sent": True, "response": result}

    async def _op_approve(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Approve a pending plan in a Jules session."""
        assert self._client is not None  # noqa: S101

        session_id = payload.get("session_id", "")
        if not session_id:
            raise ValueError("'session_id' is required for approve op")

        result = await self._client.approve_plan(session_id)
        return {"session_id": session_id, "approved": True, "response": result}

    async def _op_list(self, payload: dict[str, Any]) -> dict[str, Any]:
        """List recent Jules sessions."""
        assert self._client is not None  # noqa: S101

        page_size = payload.get("page_size", 10)
        result = await self._client.list_sessions(page_size=page_size)
        sessions = result.get("sessions", [])
        return {
            "count": len(sessions),
            "sessions": [
                {
                    "name": s.get("name", ""),
                    "title": s.get("title", ""),
                    "state": s.get("state", ""),
                    "prompt": s.get("prompt", "")[:100],
                }
                for s in sessions
            ],
        }

    async def _op_activities(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Get activity log for a Jules session."""
        assert self._client is not None  # noqa: S101

        session_id = payload.get("session_id", "")
        if not session_id:
            raise ValueError("'session_id' is required for activities op")

        result = await self._client.list_activities(session_id)
        return {"session_id": session_id, "activities": result.get("activities", [])}

    async def _op_poll(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Poll a Jules session until completion."""
        assert self._client is not None  # noqa: S101

        session_id = payload.get("session_id", "")
        if not session_id:
            raise ValueError("'session_id' is required for poll op")

        timeout = payload.get("timeout_s", 600.0)
        interval = payload.get("poll_interval_s", 15.0)

        session = await self._client.wait_for_completion(
            session_id, poll_interval_s=interval, timeout_s=timeout
        )
        return {
            "session_id": session_id,
            "final_state": session.get("state", "UNKNOWN"),
            "raw": session,
        }

    # ── Reply helper ─────────────────────────────────────────

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)


# ── Factory ──────────────────────────────────────────────────

def create_jules_agent(
    bus: MessageBus,
    tool_registry: ToolRegistry | None = None,
    *,
    api_key: str | None = None,
) -> JulesAgent:
    """Factory: create a JulesAgent with standard manifest."""
    manifest = AgentManifest(
        agent_id="jules-bridge",
        purpose="Bidirectional communication bridge to Google Jules AI coding agent",
        tools_allowed=["jules.dispatch", "jules.status", "jules.message", "jules.approve"],
        facts_writable=["session_log", "jules_result"],
        facts_readable=["*"],
        escalation_targets=["supervisor"],
        confidence_floor="C4",
        trust_level="C4",
        can_delegate=True,
        daemon=False,
        max_consecutive_errors=5,
        budget_usd=0.0,  # Jules has its own billing
    )
    return JulesAgent(
        manifest=manifest,
        bus=bus,
        tool_registry=tool_registry or ToolRegistry(),
        api_key=api_key,
    )
