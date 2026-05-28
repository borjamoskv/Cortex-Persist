"""
CORTEX v6 — Distributed Event Bus.

Allows multi-node synchronization of memories and swarm telemetry.
Transitions CORTEX from a Local Daemon to a Mesh Network.

With the L1 Signal Bus bridge, every published event can optionally
persist to SQLite for cross-process reactive signaling.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, Optional

logger = logging.getLogger("cortex.events.bus")


class DistributedEventBus:
    """Async Event Bus for cross-node Agent communication."""

    __slots__ = ("_subscribers", "_running", "_signal_bus")

    def __init__(self) -> None:
        self._subscribers: dict[
            str, list[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]
        ] = {}
        self._running = True
        self._signal_bus = None  # Optional L1 persistence bridge

    def attach_signal_bus(self, signal_bus) -> None:
        """Attach a persistent SignalBus for L1 consciousness.

        When attached, every publish() also persists the event
        to SQLite, surviving process boundaries.
        """
        self._signal_bus = signal_bus
        logger.info("L1 Signal Bus bridge attached — persistence enabled")

    def subscribe(
        self,
        topic: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe to a specific routing topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.debug("Subscribed to topic: %s", topic)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a message to all local (and eventually remote) subscribers."""
        # L1 persistence bridge: persist to SQLite if attached
        if self._signal_bus is not None:
            try:
                self._signal_bus.emit(
                    event_type=topic,
                    payload=payload,
                    source=payload.get("source", "event-bus"),
                    project=payload.get("project"),
                )
            except Exception:  # noqa: BLE001 — persistence must not break event delivery
                logger.warning(
                    "Signal Bus persistence failed for topic %s",
                    topic,
                    exc_info=True,
                )

        if topic not in self._subscribers:
            return

        tasks = [asyncio.create_task(callback(payload)) for callback in self._subscribers[topic]]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_memory(
        self,
        session_id: str,
        tenant_id: str,
        action: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Highly optimized broadcast for L1/L2 memory updates.

        Mandatory tenant isolation ensures that memory updates
        never cross boundaries.
        """
        payload = {
            "tenant_id": tenant_id,
            "session_id": session_id,
            "action": action,
            "data": data or {},
            "timestamp": "now",
        }
        await self.publish(
            topic=f"memory.{tenant_id}.{session_id}",
            payload=payload,
        )

    async def shutdown(self) -> None:
        """Graceful shutdown of the bus and all active topic workers."""
        self._running = False
        self._subscribers.clear()
        logger.info("Distributed Event Bus shut down successfully.")
