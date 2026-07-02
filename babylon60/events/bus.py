# [C5-REAL] Exergy-Maximized
"""
Distributed Event Bus.

Allows multi-node synchronization of memories and swarm telemetry.
Transitions CORTEX from a Local Daemon to a Mesh Network.

Supports Redis Streams for cross-process event synchronization, with
a transparent fallback to a local async-in-memory broker.
"""

import asyncio
import json
import logging
import os
from collections.abc import Callable, Coroutine
from typing import Any

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger("babylon60.events.bus")


class DistributedEventBus:
    """Async Event Bus for cross-node Agent communication."""

    __slots__ = ("_running", "_signal_bus", "_subscribers", "_redis", "_redis_tasks")

    def __init__(self, redis_url: str | None = None) -> None:
        self._subscribers: dict[
            str, list[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]
        ] = {}
        self._running = True
        self._signal_bus = None  # Optional L1 persistence bridge
        self._redis = None
        self._redis_tasks: list[asyncio.Task] = []

        # Connect to Redis if URL provided or found in environment
        url = redis_url or os.environ.get("REDIS_URL")
        if url and aioredis is not None:
            try:
                self._redis = aioredis.from_url(url, decode_responses=True)
                logger.info("Distributed Event Bus connected to Redis Streams: %s", url)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to connect to Redis, falling back to local RAM: %s", e)

    def attach_signal_bus(self, signal_bus) -> None:
        """Attach a persistent SignalBus for L1 consciousness.

        When attached, every publish() also persists the event
        to SQLite, surviving process boundaries.
        """
        self._signal_bus = signal_bus
        logger.info("L1 Signal Bus bridge attached - persistence enabled")

    def subscribe(
        self,
        topic: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe to a specific routing topic."""
        is_new_topic = topic not in self._subscribers
        if is_new_topic:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.debug("Subscribed to topic: %s", topic)

        # If connected to Redis and it's a new topic, spawn a background stream listener
        if self._redis is not None and is_new_topic:
            task = asyncio.create_task(self._listen_redis_stream(topic))
            self._redis_tasks.append(task)

    async def _listen_redis_stream(self, topic: str) -> None:
        """Continuously reads from a Redis Stream and dispatches to local callbacks."""
        stream_key = f"cortex:stream:{topic}"
        last_id = "$"  # Start reading from new entries only

        # Initialize stream if it doesn't exist
        try:
            assert self._redis is not None
            # Fetch current last ID to avoid reading historical junk
            info = await self._redis.xinfo_stream(stream_key)
            if info:
                last_id = info.get("last-generated-id", "$")
        except Exception:  # noqa: BLE001
            # Stream probably does not exist yet, which is fine
            last_id = "$"

        while self._running:
            try:
                assert self._redis is not None
                # Block for 1000ms waiting for new messages
                streams = await self._redis.xread({stream_key: last_id}, block=1000, count=10)
                if not streams:
                    continue

                for _, messages in streams:
                    for msg_id, data in messages:
                        last_id = msg_id
                        raw_payload = data.get("payload")
                        if raw_payload:
                            try:
                                payload = json.loads(raw_payload)
                                await self._dispatch_local(topic, payload)
                            except json.JSONDecodeError:
                                logger.warning(
                                    "Malformed JSON in stream %s message %s", stream_key, msg_id
                                )
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                logger.error("Error reading from Redis Stream %s: %s", stream_key, e)
                await asyncio.sleep(2)  # Avoid tight error loop

    async def _dispatch_local(self, topic: str, payload: dict[str, Any]) -> None:
        """Helper to invoke local callbacks for a topic."""
        callbacks = self._subscribers.get(topic, [])
        if not callbacks:
            return

        tasks = [asyncio.create_task(callback(payload)) for callback in callbacks]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a message to all local and remote subscribers."""
        # L1 persistence bridge: persist to SQLite if attached
        if self._signal_bus is not None:
            try:
                self._signal_bus.emit(
                    event_type=topic,
                    payload=payload,
                    source=payload.get("source", "event-bus"),
                    project=payload.get("project"),
                )
            except (ValueError, TypeError, RuntimeError, OSError) as e:
                logger.warning(
                    "Signal Bus persistence failed for topic %s: %s",
                    topic,
                    e,
                    exc_info=True,
                )

        # Distribute via Redis Streams if active
        if self._redis is not None:
            try:
                stream_key = f"cortex:stream:{topic}"
                # Cap the stream size to 1000 events to prevent memory/disk bloat (Thermodynamic Apoptosis limit)
                await self._redis.xadd(
                    stream_key,
                    {"payload": json.dumps(payload)},
                    maxlen=1000,
                    approximate=True,
                )
                return
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Redis stream write failed, falling back to local RAM dispatch: %s", e
                )

        # Fallback to local dispatch
        await self._dispatch_local(topic, payload)

    async def broadcast_memory(
        self,
        session_id: str,
        tenant_id: str,
        action: str,
        data: dict[str, Any] | None = None,
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

        # Cancel all background listener tasks
        for task in self._redis_tasks:
            if not task.done():
                task.cancel()

        if self._redis_tasks:
            await asyncio.gather(*self._redis_tasks, return_exceptions=True)
            self._redis_tasks.clear()

        # Close Redis connection
        if self._redis is not None:
            try:
                await self._redis.close()
                self._redis = None
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to close Redis connection during shutdown: %s", e)

        self._subscribers.clear()
        logger.info("Distributed Event Bus shut down successfully.")
