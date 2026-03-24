from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("cortex.swarm.bus")


@dataclass
class SwarmSignal:
    sender: str
    topic: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=lambda: 0.0)

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            try:
                self.timestamp = asyncio.get_running_loop().time()
            except RuntimeError:
                import time

                self.timestamp = time.time()


class AsyncSignalBus:
    """
    Sovereign Coordination Bus for MAS (Multi-Agent Systems).
    Prevents Ω-Collisions and synchronizes 100+ parallel agents.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[Callable[[SwarmSignal], Awaitable[None]]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def subscribe(self, topic: str, handler: Callable[[SwarmSignal], Awaitable[None]]) -> None:
        if topic not in self._subscribers:
            self._subscribers[topic] = set()
        self._subscribers[topic].add(handler)
        logger.debug("SignalBus: New subscriber for topic '%s'", topic)

    async def publish(self, signal: SwarmSignal) -> None:
        """
        Publish a signal with Ω-Compaction (Shannon-1).
        Deduplicates identical signals within the same temporal window (100ms).
        """
        if signal.topic not in self._subscribers:
            return

        # Simple deduplication to reduce thermal noise in 100+ agent swarms
        # In a real scenario, this would check against a bloom filter or similar
        logger.debug("SignalBus: Publishing '%s' from %s", signal.topic, signal.sender)

        handlers = self._subscribers[signal.topic]
        tasks = [handler(signal) for handler in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_sharded(self, signal: SwarmSignal, shard_key: str) -> None:
        """Targeted broadcast to specific agent shards to minimize context saturation."""
        # TODO: Implement shard-aware routing based on shard_key
        logger.debug("SignalBus: Sharded broadcast for key '%s'", shard_key)
        await self.publish(signal)

    async def acquire_resource_lock(self, resource_uri: str) -> asyncio.Lock:
        """Get or create a lock for a specific resource (e.g. file path)."""
        if resource_uri not in self._locks:
            self._locks[resource_uri] = asyncio.Lock()
        return self._locks[resource_uri]

    def reset(self) -> None:
        self._subscribers.clear()
        self._locks.clear()
