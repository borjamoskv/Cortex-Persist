"""L1 Working Memory & Swarm Bus via Redis."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

import redis.asyncio as redis

logger = logging.getLogger("cortex.storage.redis_bus")


class RedisBus:
    """L1 distributed cache and event bus for Sovereign Swarm."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        """Establish connection to Redis."""
        self._redis = redis.from_url(self._dsn, decode_responses=True)
        await self._redis.ping()
        logger.info("Connected to Redis Swarm Bus")

    async def disconnect(self):
        """Close connection to Redis."""
        if self._redis:
            await self._redis.aclose()

    async def set_context(self, tenant_id: str, key: str, value: Any, ttl: int = 3600):
        """Set an ephemeral working memory key with TTL."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        full_key = f"tenant:{tenant_id}:{key}"
        await self._redis.setex(full_key, ttl, json.dumps(value))

    async def get_context(self, tenant_id: str, key: str) -> Optional[Any]:
        """Retrieve an ephemeral working memory key."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        full_key = f"tenant:{tenant_id}:{key}"
        data = await self._redis.get(full_key)
        return json.loads(data) if data else None

    async def publish(self, channel: str, message: dict[str, Any]):
        """Publish an event to the Distributed Event Bus."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        await self._redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to a channel and yield messages asynchronously."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])
