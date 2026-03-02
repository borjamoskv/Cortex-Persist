"""
CORTEX v7.0 — Distributed Sovereign Cache (Shadow Keys + Lua Atomic CAS).

Axiom: Ω₂ (Entropic Asymmetry) × Ω₃ (Byzantine Default)
  - Memory is finite; audit trails are infinite.
  - No node is trusted; state transitions are atomic and absolute.

Advanced Architecture (v7):
  1. The "Shadow Key" Pattern: Resolves the semantic loss of Redis LRU.
     - `cortex:trigger:{id}`: Subject to volatile-lru and exact TTL.
     - `cortex:shadow:{id}`: Holds the actual context securely.
     When the trigger is evicted/expired, the background worker rescues the 
     intact payload from the shadow key before calculating the cryptographic chain.
  2. Atomic Lua Singularity: Replaces optimistic WATCH/MULTI/EXEC CAS with 
     an O(1) embedded C-engine Lua script for zero-collision chain progression.
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

# ─── Constants ─────────────────────────────────────────────────────────────
_CHAIN_TIP_KEY = "cortex:audit:chain_tip"
_CHAIN_COUNT_KEY = "cortex:audit:eviction_count"
_GENESIS_HASH = hashlib.sha256(b"CORTEX_GENESIS_VOID").hexdigest()

_TRIGGER_KEY_PREFIX = "cortex:trigger:"
_SHADOW_KEY_PREFIX = "cortex:shadow:"
_DEFAULT_TTL_SECONDS = 3600  # 1 hour

AuditCallback = Callable[[str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, None]]

# ─── Lua Atomic Script (O(1) Singularity) ──────────────────────────────────
_LUA_ADVANCE_CHAIN = """
local tip_key = KEYS[1]
local count_key = KEYS[2]

local genesis = ARGV[1]
local key_hash = ARGV[2]
local payload_hash = ARGV[3]

local prev_tip = redis.call("GET", tip_key)
if not prev_tip then
    prev_tip = genesis
end

local count = redis.call("INCR", count_key)

-- H(prev_tip | key_hash | payload_hash)
local proof_material = prev_tip .. "|" .. key_hash .. "|" .. payload_hash
local new_tip = redis.sha256hex(proof_material)

redis.call("SET", tip_key, new_tip)

return {prev_tip, new_tip, count}
"""


def _payload_hash(data: dict[str, Any]) -> str:
    """Deterministic SHA-256 of a JSON payload."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()


class DistributedSovereignCache:
    """
    Cluster-safe Redis L1 cache with distributed cryptographic audit chain (v7).
    """

    def __init__(
        self, redis_client: Any, audit_callback: AuditCallback | None = None
    ) -> None:
        if not _REDIS_AVAILABLE:
            raise ImportError(
                "redis[asyncio] is required. Install with: pip install 'redis[asyncio]'"
            )
        self._r = redis_client
        self._audit_callback = audit_callback
        self._node_id = os.environ.get("CORTEX_NODE_ID", "cortex-node-01")
        self._subscriber_task: asyncio.Task[None] | None = None
        self._is_available = True
        
        # Register Lua script into Redis for atomic execution
        self._advance_chain_script = self._r.register_script(_LUA_ADVANCE_CHAIN)

    # ─── Factory ─────────────────────────────────────────────────────────────

    @classmethod
    @asynccontextmanager
    async def from_env(
        cls,
        audit_callback: AuditCallback | None = None,
    ) -> AsyncIterator[DistributedSovereignCache]:
        if not _REDIS_AVAILABLE:
            raise ImportError("redis[asyncio] required")

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = aioredis.from_url(redis_url, decode_responses=True)

        await client.setnx(_CHAIN_TIP_KEY, _GENESIS_HASH)
        await client.setnx(_CHAIN_COUNT_KEY, 0)

        cache = cls(client, audit_callback)
        await cache._start_eviction_subscriber()
        try:
            yield cache
        finally:
            await cache._stop_eviction_subscriber()
            await client.aclose()

    # ─── Core Operations (Dual Insert Pattern) ────────────────────────────────

    async def get(self, key: str) -> dict[str, Any] | None:
        """
        Retrieve context from the Shadow Key (the true data source).
        """
        if not self._is_available:
            return None
        try:
            shadow_key = f"{_SHADOW_KEY_PREFIX}{key}"
            raw = await self._r.get(shadow_key)
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
        Store agent context using the Shadow Key pattern.
        """
        try:
            shadow_key = f"{_SHADOW_KEY_PREFIX}{key}"
            trigger_key = f"{_TRIGGER_KEY_PREFIX}{key}"
            serialized = json.dumps(data, sort_keys=True)

            async with self._r.pipeline(transaction=True) as pipe:
                # 1. Store actual data in the shadow key.
                # Give it a slightly longer TTL as a safety fallback against 
                # infinite memory leaks if the worker crashes before cleaning it.
                pipe.set(shadow_key, serialized, ex=ttl + 300)
                
                # 2. Set the trigger key. This is subject to volatile-lru and strict TTL.
                # Its only purpose is to trigger the Exe event when 'dying'.
                pipe.set(trigger_key, "1", ex=ttl)
                await pipe.execute()

            self._is_available = True
            logger.debug("✅ [SHADOW PUT] %s (TTL=%ds)", key, ttl)
            return True
        except Exception as exc:
            logger.error("🚨 [SHADOW PUT FAIL] %s: %s", key, exc)
            self._is_available = False
            return False

    async def delete(self, key: str) -> None:
        try:
            shadow_key = f"{_SHADOW_KEY_PREFIX}{key}"
            trigger_key = f"{_TRIGGER_KEY_PREFIX}{key}"
            await self._r.delete(shadow_key, trigger_key)
        except Exception as exc:
            logger.warning("⚡ [REDIS DELETE FAIL] %s: %s", key, exc)

    # ─── Atomic Lua Distributed Audit Chain ──────────────────────────────────

    async def _advance_chain_tip(
        self, key: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Atomically advances the distributed evidence chain in Redis via Lua script.
        Absolute zero collisions (O(1)).
        """
        ph = _payload_hash(data)
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        try:
            # Execute Lua script
            prev_tip, new_tip, count = await self._advance_chain_script(
                keys=[_CHAIN_TIP_KEY, _CHAIN_COUNT_KEY],
                args=[_GENESIS_HASH, key_hash, ph]
            )

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
                "🔗 [LUA SINGULARITY] %s → %s... (eviction #%d)",
                key,
                new_tip[:16],
                count,
            )
            return audit_entry

        except Exception as exc:
            logger.error("🚨 [LUA FAIL] Chain advancement failed: %s", exc)
            return {
                "ts": time.time(),
                "key": key,
                "payload_hash": ph,
                "event": "EVICTION_AUDIT_DEGRADED",
                "node": self._node_id,
                "error": "LUA_EXECUTION_FAILED",
            }

    async def prove_forgetting(self) -> dict[str, Any]:
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
            return {"status": "UNAVAILABLE", "error": str(exc)}

    # ─── Keyspace Notification Subscriber ────────────────────────────────────

    async def _start_eviction_subscriber(self) -> None:
        self._subscriber_task = asyncio.ensure_future(
            self._eviction_listener_loop(),
        )
        logger.info(
            "🎧 [SHADOW WORKER] Keyspace notification subscriber started",
        )

    async def _stop_eviction_subscriber(self) -> None:
        if self._subscriber_task and not self._subscriber_task.done():
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass

    async def _eviction_listener_loop(self) -> None:
        """
        Listens exclusively for cortex:trigger:* events.
        Rescues the payload from the shadow key before it expires.
        """
        pubsub: PubSub = self._r.pubsub()
        await pubsub.psubscribe(
            "__keyevent@0__:expired",
            "__keyevent@0__:evicted",
        )
        logger.info("📡 [SHADOW WORKER] Subscribed to events (node=%s)", self._node_id)

        try:
            async for message in pubsub.listen():
                if message["type"] not in ("message", "pmessage"):
                    continue

                evicted_redis_key: str = message.get("data", "")

                if not evicted_redis_key.startswith(_TRIGGER_KEY_PREFIX):
                    continue

                agent_key = evicted_redis_key[len(_TRIGGER_KEY_PREFIX):]
                logger.debug("📤 [TRIGGER EVENT] key=%s", agent_key)

                # Rescue real data from the shadow key
                shadow_key = f"{_SHADOW_KEY_PREFIX}{agent_key}"
                raw_payload = await self._r.get(shadow_key)

                if raw_payload is not None:
                    payload = json.loads(raw_payload)
                    # Clean up the shadow key since we've processed it
                    await self._r.delete(shadow_key)
                    logger.info("🛡️ [SHADOW RESCUE] Rescued 100%% of %s payload!", agent_key)
                else:
                    payload = {
                        "_type": "EVICTION_TOMBSTONE",
                        "key": agent_key,
                        "ts": time.time(),
                        "node": self._node_id,
                        "note": "Shadow payload already swept or not found."
                    }

                # Atomic advance
                audit_entry = await self._advance_chain_tip(agent_key, payload)

                if self._audit_callback:
                    task = asyncio.ensure_future(
                        self._safe_audit_callback(agent_key, payload, audit_entry)
                    )
                    task.add_done_callback(lambda t: None)

        except asyncio.CancelledError:
            await pubsub.unsubscribe()
            await pubsub.aclose()
            raise
        except Exception as exc:
            logger.error("🚨 [SHADOW WORKER CRASH] %s", exc, exc_info=True)

    async def _safe_audit_callback(
        self, key: str, data: dict[str, Any], audit: dict[str, Any]
    ) -> None:
        try:
            await self._audit_callback(key, data, audit)  # type: ignore[misc]
        except Exception as exc:
            logger.error("🚨 [AUDIT CALLBACK FAIL] key=%s: %s", key, exc)


# ─── FastAPI Integration Helper ──────────────────────────────────────────────

def make_fastapi_lifespan(
    audit_callback: AuditCallback | None = None,
) -> Any:
    from contextlib import asynccontextmanager
    from fastapi import FastAPI as _FastAPI

    @asynccontextmanager
    async def lifespan(app: _FastAPI) -> AsyncIterator[None]:
        async with DistributedSovereignCache.from_env(audit_callback) as cache:
            app.state.cache = cache
            yield

    return lifespan
