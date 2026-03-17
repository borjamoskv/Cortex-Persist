"""CORTEX Agent Runtime — Base Agent.

BaseAgent provides the event loop, message handling, and lifecycle
management that distinguishes an agent from a tool.

Subclasses implement:
    - handle_message(message) — react to incoming messages
    - tick() — periodic autonomous work (daemons override this)

The loop: heartbeat → receive → handle_message/tick → repeat.
Auto-quarantine after max_consecutive_errors.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.state import AgentState, AgentStatus, WorkingMemory
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.base")


class BaseAgent:
    """Abstract base agent with async event loop.

    Provides:
        - Continuous run loop with heartbeat
        - Message receive/dispatch
        - Automatic quarantine on repeated failures
        - Isolated WorkingMemory
        - Tool access governed by manifest policy
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,  # MessageBus protocol
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self.manifest = manifest
        self.bus = bus
        self.tools = tool_registry or ToolRegistry()
        self.state = AgentState()
        self.memory = WorkingMemory()
        self._task: Optional[asyncio.Task[None]] = None

    @property
    def agent_id(self) -> str:
        return self.manifest.agent_id

    # ── Abstract methods (subclasses implement) ──────────────────

    async def handle_message(self, message: AgentMessage) -> None:
        """Process an incoming message. Subclasses MUST override."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement handle_message()")

    async def tick(self) -> None:
        """Periodic autonomous work. Daemons override this.

        Default implementation is a no-op for reactive agents.
        """

    async def on_start(self) -> None:
        """Hook called once when the agent starts running."""

    async def on_stop(self) -> None:
        """Hook called once when the agent stops."""

    # ── Event loop ───────────────────────────────────────────────

    async def run(self) -> None:
        """Main event loop. Runs until stopped or quarantined."""
        self.state.status = AgentStatus.RUNNING
        logger.info("[%s] Agent started", self.agent_id)

        try:
            await self.on_start()
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] on_start failed: %s", self.agent_id, exc)
            self.state.status = AgentStatus.FAILED
            return

        while self.state.status == AgentStatus.RUNNING:
            try:
                self.state.last_heartbeat_ts = time.time()

                # Try to receive a message
                msg = await self.bus.receive(self.agent_id, timeout=1.0)

                if msg is not None:
                    # Handle shutdown signals
                    if msg.kind == MessageKind.SHUTDOWN:
                        logger.info("[%s] Received SHUTDOWN", self.agent_id)
                        break

                    await self.handle_message(msg)
                    self.state.record_message_processed()
                    self.state.record_success()
                else:
                    # No message — run periodic tick
                    await self.tick()
                    self.state.record_success()

            except Exception as exc:  # noqa: BLE001
                self.state.record_error(repr(exc))
                logger.warning(
                    "[%s] Error (consecutive=%d): %s",
                    self.agent_id,
                    self.state.consecutive_errors,
                    exc,
                )

                # Auto-quarantine after too many consecutive errors
                if self.state.consecutive_errors >= self.manifest.max_consecutive_errors:
                    self.state.status = AgentStatus.QUARANTINED
                    logger.error(
                        "[%s] QUARANTINED after %d consecutive errors",
                        self.agent_id,
                        self.state.consecutive_errors,
                    )
                    break

                # Brief backoff before retrying
                await asyncio.sleep(0.5)

        # Cleanup — preserve terminal statuses (QUARANTINED, FAILED)
        try:
            await self.on_stop()
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] on_stop failed: %s", self.agent_id, exc)

        if self.state.status not in (
            AgentStatus.QUARANTINED,
            AgentStatus.FAILED,
        ):
            self.state.status = AgentStatus.IDLE

        logger.info(
            "[%s] Agent stopped (status=%s, msgs=%d, errors=%d)",
            self.agent_id,
            self.state.status.value,
            self.state.total_messages_processed,
            self.state.error_count,
        )

    # ── Lifecycle control ────────────────────────────────────────

    async def start(self) -> asyncio.Task[None]:
        """Start the agent as an asyncio task."""
        if self._task is not None and not self._task.done():
            raise RuntimeError(f"Agent {self.agent_id} is already running")
        self._task = asyncio.create_task(self.run(), name=f"agent-{self.agent_id}")
        return self._task

    async def stop(self) -> None:
        """Request graceful shutdown via message bus."""
        shutdown_msg = new_message(
            sender="supervisor",
            recipient=self.agent_id,
            kind=MessageKind.SHUTDOWN,
            payload={},
        )
        await self.bus.send(shutdown_msg)

    def force_stop(self) -> None:
        """Force-cancel the agent task."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
            # Preserve terminal statuses set by supervisor/quarantine
            if self.state.status not in (
                AgentStatus.QUARANTINED,
                AgentStatus.FAILED,
            ):
                self.state.status = AgentStatus.IDLE

    # ── Tool access (policy-governed) ────────────────────────────

    async def use_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Invoke a tool respecting manifest policy."""
        tool = self.tools.get(tool_name, allowed=self.manifest.tools_allowed or None)
        return await tool.execute(**kwargs)

    # ── Messaging helpers ────────────────────────────────────────

    async def send_result(
        self,
        recipient: str,
        result: Any,
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Send a task result to another agent."""
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.TASK_RESULT,
            payload={"result": result},
            correlation_id=correlation_id if correlation_id is not None else "auto",
        )
        await self.bus.send(msg)

    async def request_task(
        self,
        recipient: str,
        task_payload: dict[str, Any],
    ) -> None:
        """Request another agent to perform a task."""
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.TASK_REQUEST,
            payload=task_payload,
        )
        await self.bus.send(msg)

    async def emit_heartbeat(self) -> None:
        """Emit a heartbeat message to the supervisor."""
        msg = new_message(
            sender=self.agent_id,
            recipient="supervisor",
            kind=MessageKind.HEARTBEAT,
            payload={
                "status": self.state.status.value,
                "errors": self.state.error_count,
                "messages_processed": self.state.total_messages_processed,
                "ts": time.time(),
            },
        )
        await self.bus.send(msg)
