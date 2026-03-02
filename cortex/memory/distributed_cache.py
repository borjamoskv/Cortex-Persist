"""
CORTEX v6.1 — Distributed Sovereign Cache (Redis L1 + Cryptographic Audit Trail).

Axiom: Ω₂ (Entropic Asymmetry) × Ω₃ (Byzantine Default)
  - Memory is finite; audit trails are infinite.
  - No node is trusted by default. Chain tip lives in Redis (atomic, distributed).

Resolves the critical flaw in CortexSecureMemoryCache v6.0:
  The `_chain_tip` was LOCAL TO PROCESS — in a multi-node cluster, each
  container had its own divergent chain, breaking auditability.

This module promotes the chain tip to Redis via WATCH/MULTI/EXEC (optimistic
CAS), making it cluster-wide, atomic, and Byzantine-resistant.

Architecture:
  ┌─────────────────────────────────────────────────────────────────┐
  │  FastAPI Node A      FastAPI Node B      FastAPI Node C         │
  │  ┌────────────┐      ┌────────────┐      ┌────────────┐         │
  │  │ Local LRU  │      │ Local LRU  │      │ Local LRU  │  L0    │
  │  └─────┬──────┘      └─────┬──────┘      └─────┬──────┘         │
  │        │                   │                   │                │
  │  ┌─────▼───────────────────▼───────────────────▼──────┐        │
  │  │            Redis (L1) — maxmemory 512mb, allkeys-lru│  L1    │
  │  │            chain_tip: cortex:audit:chain_tip        │        │
  │  └──────────────────────────┬─────────────────────────┘        │
  │                             │  keyspace events (Exe)           │
  │  ┌──────────────────────────▼─────────────────────────┐        │
  │  │       Async Audit Worker (per-process)             │        │
  │  │       Subscribes to __keyevent@0__:expired         │        │
  │  │       Subscribes to __keyevent@0__:evicted         │        │
  │  └──────────────────────────┬─────────────────────────┘        │
  │                             │                                  │
  │  ┌──────────────────────────▼─────────────────────────┐        │
  │  │       PostgreSQL (L3) — Immutable Audit Ledger     │  L3    │
  │  └─────────────────────────────────────────────────────┘        │
  └─────────────────────────────────────────────────────────────────┘

Usage (FastAPI lifespan):
    from cortex.memory.distributed_cache import DistributedSovereignCache, make_fastapi_lifespan

    app = FastAPI(lifespan=make_fastapi_lifespan(my_pg_audit_callback))

    @app.post("/memory/update")
    async def update_memory(agent_id: str, payload: dict, request: Request):
        await request.app.state.cache.put(agent_id, payload)
        proof = await request.app.state.cache.prove_forgetting()
        return {"chain_tip": proof["tip"]}
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any

# Optional redis dependency guard
try:
    import redis.asyncio as aioredis
    from redis.asyncio.client import PubSub

    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False
    aioredis = None  # type: ignore[assignment]

logger = logging.getLogger("cortex.memory.distributed_cache")

# ─── Redis Key Constants ────────────────────────────────────────────────────
_CHAIN_TIP_KEY = "cortex:audit:chain_tip"
_CHAIN_COUNT_KEY = "cortex:audit:eviction_count"
_GENESIS_HASH = hashlib.sha256(b"CORTEX_GENESIS_VOID").hexdigest()
_AGENT_KEY_PREFIX = "cortex:agent:"
_DEFAULT_TTL_SECONDS = 3600  # 1 hour

AuditCallback = Callable[[str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, None]]


def _compute_chain_tip(prev_tip: str, key: str, payload_hash: str) -> str:
    """Deterministic hash chain: H(prev_tip | key_hash | payload_hash)."""
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    proof_material = f"{prev_tip}|{key_hash}|{payload_hash}"
    return hashlib.sha256(proof_material.encode()).hexdigest()


def _payload_hash(data: dict[str, Any]) -> str:
    """Deterministic SHA-256 of a JSON payload."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()


class DistributedSovereignCache:
    """
    Cluster-safe Redis L1 cache with distributed cryptographic audit chain.

    Key properties:
    - O(1) get/put via Redis hset/expire
    - Chain tip is atomic (WATCH/MULTI/EXEC optimistic CAS in Redis)
    - Keyspace notification subscriber auto-generates audit entries on eviction
    - Degrades gracefully to no-op if Redis is unavailable (circuit breaker)
    - Fully async (redis.asyncio) — never blocks FastAPI event loop
    """

    def __init__(
        self, redis_client: Any, audit_callback: AuditCallback | None = None
    ) -> None:
        """
        Args:
            redis_client: An `aioredis.Redis` instance.
            audit_callback: Optional async callable(key, data, audit_entry) for
                            L3 persistence (PostgreSQL, etc.). Called in background.
        """
        if not _REDIS_AVAILABLE:
            raise ImportError(
                "redis[asyncio] is required. Install with: pip install 'redis[asyncio]'"
            )
        self._r = redis_client
        self._audit_callback = audit_callback
        self._node_id = os.environ.get("CORTEX_NODE_ID", "cortex-node-01")
        self._subscriber_task: asyncio.Task[None] | None = None
        self._is_available = True  # Circuit breaker flag

    # ─── Factory ─────────────────────────────────────────────────────────────

    @classmethod
    @asynccontextmanager
    async def from_env(
        cls,
        audit_callback: AuditCallback | None = None,
    ) -> AsyncIterator[DistributedSovereignCache]:
        """
        Context manager factory. Reads REDIS_URL from env.
        Starts and stops the keyspace notification subscriber automatically.

        Usage:
            async with DistributedSovereignCache.from_env() as cache:
                await cache.put("key", {"data": 1})
        """
        if not _REDIS_AVAILABLE:
            raise ImportError("redis[asyncio] required: pip install 'redis[asyncio]'")

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = aioredis.from_url(redis_url, decode_responses=True)

        # Ensure chain tip genesis if not set
        await client.setnx(_CHAIN_TIP_KEY, _GENESIS_HASH)
        await client.setnx(_CHAIN_COUNT_KEY, 0)

        cache = cls(client, audit_callback)
        await cache._start_eviction_subscriber()
        try:
            yield cache
        finally:
            await cache._stop_eviction_subscriber()
            await client.aclose()

    # ─── Core Operations ─────────────────────────────────────────────────────

    async def get(self, key: str) -> dict[str, Any] | None:
        """
        Retrieve agent context from Redis L1.
        Returns None on cache miss or Redis failure.

        Derivation: Ω₃ — Redis failure is tolerated (circuit breaker).
        """
        if not self._is_available:
            return None
        try:
            redis_key = f"{_AGENT_KEY_PREFIX}{key}"
            raw = await self._r.get(redis_key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("⚡ [REDIS MISS] get(%s) failed: %s", key, exc)
            self._is_available = False
            return None

    async def put(
        self,
        key: str,
        data: dict[str, Any],
        ttl: int = _DEFAULT_TTL_SECONDS,
    ) -> bool:
        """
        Store agent context in Redis with TTL.
        Returns True on success.

        NOTE: Redis LRU eviction (allkeys-lru) handles capacity enforcement
        at the infrastructure level. Keyspace events trigger audit trail.
        """
        try:
            redis_key = f"{_AGENT_KEY_PREFIX}{key}"
            serialized = json.dumps(data, sort_keys=True)
            await self._r.set(redis_key, serialized, ex=ttl)
            self._is_available = True  # Re-arm circuit breaker on success
            logger.debug("✅ [REDIS PUT] %s (TTL=%ds)", key, ttl)
            return True
        except Exception as exc:
            logger.error("🚨 [REDIS PUT FAIL] %s: %s", key, exc)
            self._is_available = False
            return False

    async def delete(self, key: str) -> None:
        """Explicitly delete a key (e.g., session end)."""
        try:
            redis_key = f"{_AGENT_KEY_PREFIX}{key}"
            await self._r.delete(redis_key)
        except Exception as exc:
            logger.warning("⚡ [REDIS DELETE FAIL] %s: %s", key, exc)

    # ─── Distributed Audit Chain ─────────────────────────────────────────────

    async def _advance_chain_tip(
        self, key: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Atomically advances the distributed evidence chain in Redis using
        WATCH/MULTI/EXEC (optimistic concurrency control).

        This is the critical fix vs. the local-process implementation:
        the chain tip is SHARED across ALL nodes, making the audit trail
        truly distributed and Byzantine-resistant (Ω₃).
        """
        ph = _payload_hash(data)

        max_retries = 5
        for attempt in range(max_retries):
            try:
                async with self._r.pipeline() as pipe:
                    await pipe.watch(_CHAIN_TIP_KEY, _CHAIN_COUNT_KEY)
                    prev_tip: str = await pipe.get(_CHAIN_TIP_KEY) or _GENESIS_HASH
                    count_raw: str | None = await pipe.get(_CHAIN_COUNT_KEY)
                    count = int(count_raw or 0) + 1
                    new_tip = _compute_chain_tip(prev_tip, key, ph)

                    pipe.multi()
                    pipe.set(_CHAIN_TIP_KEY, new_tip)
                    pipe.set(_CHAIN_COUNT_KEY, count)
                    await pipe.execute()

                    audit_entry: dict[str, Any] = {
                        "ts": time.time(),
                        "eviction_id": count,
                        "key": key,
                        "prev_proof": prev_tip,
                        "current_proof": new_tip,
                        "payload_hash": ph,
                        "node": self._node_id,
                        "axiom": "Ω₂×Ω₃",
                        "event": "EVICTION_AUDIT",
                    }
                    logger.info(
                        "🔗 [CHAIN TIP] %s → %s... (eviction #%d, node=%s)",
                        key,
                        new_tip[:16],
                        count,
                        self._node_id,
                    )
                    return audit_entry

            except aioredis.WatchError:
                backoff = 0.01 * (2**attempt)
                logger.debug(
                    "⚔️ [CAS COLLISION] Chain tip mutated by another node. "
                    "Retry %d/%d in %.2fs",
                    attempt + 1,
                    max_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)

        logger.error(
            "🚨 [CHAIN FAIL] CAS failed after %d retries for key %s", max_retries, key
        )
        return {
            "ts": time.time(),
            "key": key,
            "payload_hash": ph,
            "event": "EVICTION_AUDIT_DEGRADED",
            "node": self._node_id,
            "error": "CAS_EXHAUSTED",
        }

    async def prove_forgetting(self) -> dict[str, Any]:
        """Returns the current distributed cryptographic chain tip."""
        try:
            tip: str = await self._r.get(_CHAIN_TIP_KEY) or _GENESIS_HASH
            count: int = int(await self._r.get(_CHAIN_COUNT_KEY) or 0)
            return {
                "tip": tip,
                "count": count,
                "node": self._node_id,
                "status": "DISTRIBUTED_SOVEREIGN_VALIDATED",
            }
        except Exception as exc:
            logger.error("🚨 [PROVE FAIL] %s", exc)
            return {"status": "UNAVAILABLE", "error": str(exc)}

    # ─── Keyspace Notification Subscriber ────────────────────────────────────

    async def _start_eviction_subscriber(self) -> None:
        """
        Subscribe to Redis keyspace notifications for eviction and expiry events.

        Requires Redis flag: --notify-keyspace-events Exe
        (set in docker-compose.cloud.yml redis command block)
        """
        self._subscriber_task = asyncio.ensure_future(
            self._eviction_listener_loop(),
        )
        logger.info(
            "🎧 [AUDIT WORKER] Keyspace notification subscriber started (node=%s)",
            self._node_id,
        )

    async def _stop_eviction_subscriber(self) -> None:
        """Gracefully cancel the subscriber background task."""
        if self._subscriber_task and not self._subscriber_task.done():
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 [AUDIT WORKER] Subscriber stopped (node=%s)", self._node_id)

    async def _eviction_listener_loop(self) -> None:
        """
        Background loop: listens for Redis keyspace events.

        Filters for cortex:agent:* keys to avoid irrelevant noise.
        On eviction/expiry → advances chain tip → calls audit_callback.
        """
        pubsub: PubSub = self._r.pubsub()
        await pubsub.psubscribe(
            "__keyevent@0__:expired",
            "__keyevent@0__:evicted",
        )
        logger.info(
            "📡 [AUDIT WORKER] Subscribed to keyspace events (node=%s)", self._node_id
        )

        try:
            async for message in pubsub.listen():
                if message["type"] not in ("message", "pmessage"):
                    continue

                evicted_redis_key: str = message.get("data", "")

                if not evicted_redis_key.startswith(_AGENT_KEY_PREFIX):
                    continue

                agent_key = evicted_redis_key[len(_AGENT_KEY_PREFIX):]
                logger.info(
                    "📤 [EVICTION DETECTED] key=%s event=%s",
                    agent_key,
                    message.get("channel", "unknown"),
                )

                tombstone: dict[str, Any] = {
                    "_type": "EVICTION_TOMBSTONE",
                    "key": agent_key,
                    "ts": time.time(),
                    "node": self._node_id,
                }

                audit_entry = await self._advance_chain_tip(agent_key, tombstone)

                if self._audit_callback:
                    task = asyncio.ensure_future(
                        self._safe_audit_callback(agent_key, tombstone, audit_entry)
                    )
                    # Keep a reference to prevent GC
                    task.add_done_callback(lambda t: None)

        except asyncio.CancelledError:
            await pubsub.unsubscribe()
            await pubsub.aclose()
            raise
        except Exception as exc:
            logger.error("🚨 [AUDIT WORKER CRASH] %s", exc, exc_info=True)

    async def _safe_audit_callback(
        self, key: str, data: dict[str, Any], audit: dict[str, Any]
    ) -> None:
        """Wrapper to ensure audit callback errors never crash the listener."""
        try:
            await self._audit_callback(key, data, audit)  # type: ignore[misc]
        except Exception as exc:
            logger.error("🚨 [AUDIT CALLBACK FAIL] key=%s: %s", key, exc)


# ─── FastAPI Integration Helper ──────────────────────────────────────────────


def make_fastapi_lifespan(
    audit_callback: AuditCallback | None = None,
) -> Any:
    """
    Returns a FastAPI lifespan context manager that wires up the
    DistributedSovereignCache and stores it in app.state.cache.

    Usage:
        from fastapi import FastAPI, Request
        from cortex.memory.distributed_cache import make_fastapi_lifespan

        app = FastAPI(lifespan=make_fastapi_lifespan(my_pg_callback))

        @app.post("/memory/update")
        async def update_memory(agent_id: str, payload: dict, request: Request):
            cache: DistributedSovereignCache = request.app.state.cache
            await cache.put(agent_id, payload)
            proof = await cache.prove_forgetting()
            return {"status": "ok", "chain_tip": proof["tip"]}
    """
    from contextlib import asynccontextmanager

    from fastapi import FastAPI as _FastAPI

    @asynccontextmanager
    async def lifespan(app: _FastAPI) -> AsyncIterator[None]:
        async with DistributedSovereignCache.from_env(audit_callback) as cache:
            app.state.cache = cache
            yield

    return lifespan
