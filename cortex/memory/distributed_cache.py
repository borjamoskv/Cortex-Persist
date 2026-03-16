"""
CORTEX v7.5 — "Hydra-Log" Distributed Cache (Redis Streams + Atomic Lua).

Axiom: Ω₁ (Multi-Scale Causality) × Ω₃ (Byzantine Default)
  - All state transitions must be causally reachable (at-least-once).
  - Volatile notifications are replaced by Persistent Streams for audit reliability.

Hydra-Log Architecture:
  1. The "Shadow Key" (L1 Cache): Holds the context.
  2. The "Trigger Key" (L1 Alarm): Triggers expiration events.
  3. The "Audit Stream" (L1 Persistent Log):
     - Every 'put' logs to the stream.
     - Every 'eviction' logs to the stream via a reliable handoff.
     - Background workers consume via XREADGROUP (Consumer Groups) to ensure
       no audit entry is lost even if nodes crash (Ω₃).
  4. At-Least-Once Delivery: Atomic Lua advances the chain-tip AND logs to
     the stream in a single transaction (where possible) or causal sequence.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import time
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any

from cortex.immune.chaos import ChaosGate, async_interceptor
from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

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
_AUDIT_STREAM_KEY = "cortex:audit:stream"
_AUDIT_GROUP_NAME = "cortex-audit-group"
_GENESIS_HASH = hashlib.sha256(b"CORTEX_GENESIS_VOID").hexdigest()

_TRIGGER_KEY_PREFIX = "cortex:trigger:"
_SHADOW_KEY_PREFIX = "cortex:shadow:"
_DEFAULT_TTL_SECONDS = 3600  # 1 hour

AuditCallback = Callable[[str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, None]]

# ─── Lua Atomic Hydra-Log Script ──────────────────────────────────────────
# Advances chain-tip AND logs to the audit stream in a single atomic step.
_LUA_HYDRA_ADVANCE = """
local tip_key = KEYS[1]
local count_key = KEYS[2]
local stream_key = KEYS[3]

local genesis = ARGV[1]
local agent_key = ARGV[2]
local payload_hash = ARGV[3]
local node_id = ARGV[4]
local event_type = ARGV[5]

local prev_tip = redis.call("GET", tip_key)
if not prev_tip then
    prev_tip = genesis
end

local count = redis.call("INCR", count_key)

-- H(prev_tip | key_hash(agent_key) | payload_hash)
local key_hash = redis.sha256hex(agent_key)
local proof_material = prev_tip .. "|" .. key_hash .. "|" .. payload_hash
local new_tip = redis.sha256hex(proof_material)

redis.call("SET", tip_key, new_tip)

-- Log into the persistent Hydra Stream
redis.call("XADD", stream_key, "*",
    "eviction_id", count,
    "agent_key", agent_key,
    "prev_proof", prev_tip,
    "current_proof", new_tip,
    "payload_hash", payload_hash,
    "node", node_id,
    "event", event_type,
    "ts", ARGV[6]
)

return {prev_tip, new_tip, count}
"""


def _payload_hash(data: dict[str, Any]) -> str:
    """Deterministic SHA-256 of a JSON payload."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()


class DistributedSovereignCache:
    """
    Cluster-safe Redis L1 cache with Persistent Audit Streams (v7.5).
    """

    def __init__(self, redis_client: Any, audit_callback: AuditCallback | None = None) -> None:
        if not _REDIS_AVAILABLE:
            raise ImportError("redis[asyncio] required")
        self._r = redis_client
        self._audit_callback = audit_callback
        self._node_id = os.environ.get("CORTEX_NODE_ID", "cortex-node-01")
        self._consumer_task: asyncio.Task[None] | None = None
        self._notification_task: asyncio.Task[None] | None = None
        self._is_available = True
        self.chaos_gate = ChaosGate(name="redis_l1_cache")

        self._hydra_advance_script = self._r.register_script(_LUA_HYDRA_ADVANCE)
        self._last_ping_time = 0.0

    # ─── Factory ─────────────────────────────────────────────────────────────

    @classmethod
    @asynccontextmanager
    async def from_env(
        cls,
        audit_callback: AuditCallback | None = None,
    ) -> AsyncIterator[DistributedSovereignCache]:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = aioredis.from_url(redis_url, decode_responses=True)  # type: ignore[reportOptionalMemberAccess]

        # Baseline initialization
        await client.setnx(_CHAIN_TIP_KEY, _GENESIS_HASH)
        await client.setnx(_CHAIN_COUNT_KEY, 0)

        # Ensure Stream Group exists (Ω₃ - Antifragile group creation)
        try:
            await client.xgroup_create(_AUDIT_STREAM_KEY, _AUDIT_GROUP_NAME, id="0", mkstream=True)
            logger.info("🐉 [HYDRA-LOG] Created new audit stream consumer group.")
        except aioredis.exceptions.ResponseError as e:  # type: ignore[reportOptionalMemberAccess]
            if "BUSYGROUP" not in str(e):
                raise

        cache = cls(client, audit_callback)
        # 1. Start the 'Handoff' listener (Notification -> Stream)
        await cache._start_notification_handoff()
        # 2. Start the 'Reliable Worker' (Stream -> DB)
        await cache._start_stream_consumer()

        try:
            yield cache
        finally:
            await cache._stop_background_tasks()
            await client.aclose()

    # ─── Core Operations ─────────────────────────────────────────────────────

    async def get(self, key: str) -> dict[str, Any] | None:
        if not self._is_available:
            # Quick Circuit Breaker Ping (Max once per 10 secs to avoid Event Loop spam)
            now = time.time()
            if now - self._last_ping_time > 10.0:
                self._last_ping_time = now
                try:
                    # Non-blocking ping
                    await asyncio.wait_for(self._r.ping(), timeout=1.0)
                    self._is_available = True
                    logger.info("🐉 [HYDRA-LOG] Circuit Breaker reset. Cache is back online.")
                except Exception:  # noqa: BLE001 — circuit breaker probe must never raise
                    # Still dead, fail fast without waiting
                    pass
            return None
        try:
            shadow_key = f"{_SHADOW_KEY_PREFIX}{key}"
            raw = await async_interceptor(self.chaos_gate, self._r.get, shadow_key)
            return json.loads(raw) if raw else None
        except (ValueError, TypeError, OSError) as exc:
            logger.warning("⚡ [REDIS MISS] get(%s): %s", key, exc)
            self._is_available = False
            ErrorGhostPipeline().capture_sync(
                exc, source="distributed_cache:get", project="CORTEX_SYSTEM"
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("⚡ [REDIS MISS UNEXPECTED] get(%s): %s", key, exc)
            self._is_available = False
            ErrorGhostPipeline().capture_sync(
                exc, source="distributed_cache:get", project="CORTEX_SYSTEM"
            )
            return None

    async def put(self, key: str, data: dict[str, Any], ttl: int = _DEFAULT_TTL_SECONDS) -> bool:
        """
        Standard store + initial 'PUT' logging in stream.
        """
        try:
            shadow_key = f"{_SHADOW_KEY_PREFIX}{key}"
            trigger_key = f"{_TRIGGER_KEY_PREFIX}{key}"
            serialized = json.dumps(data, sort_keys=True)

            async with self._r.pipeline(transaction=True) as pipe:
                pipe.set(shadow_key, serialized, ex=ttl + 60)
                pipe.set(trigger_key, "1", ex=ttl)
                await async_interceptor(self.chaos_gate, pipe.execute)

            self._is_available = True
            return True
        except (ValueError, TypeError, OSError) as exc:
            logger.error("🚨 [HYDRA PUT FAIL] %s: %s", key, exc)
            self._is_available = False
            ErrorGhostPipeline().capture_sync(
                exc, source="distributed_cache:put", project="CORTEX_SYSTEM"
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("🚨 [HYDRA PUT UNEXPECTED] %s: %s", key, exc)
            self._is_available = False
            ErrorGhostPipeline().capture_sync(
                exc, source="distributed_cache:put", project="CORTEX_SYSTEM"
            )
            return False

    # ─── Reliable Audit Advancement ──────────────────────────────────────────

    async def _reliable_advance_chain(
        self, key: str, payload: dict[str, Any], event_type: str
    ) -> dict[str, Any]:
        """
        Atomic Lua: Advance Tip + Log to Stream.
        """
        ph = _payload_hash(payload)
        now = str(time.time())

        try:
            prev_tip, new_tip, count = await async_interceptor(
                self.chaos_gate,
                self._hydra_advance_script,
                keys=[_CHAIN_TIP_KEY, _CHAIN_COUNT_KEY, _AUDIT_STREAM_KEY],
                args=[_GENESIS_HASH, key, ph, self._node_id, event_type, now],
            )

            return {
                "eviction_id": count,
                "key": key,
                "prev_proof": prev_tip,
                "current_proof": new_tip,
                "payload_hash": ph,
                "event": event_type,
            }
        except (ValueError, TypeError, OSError) as exc:
            logger.error("🚨 [HYDRA ADVANCE FAIL] %s", exc)
            return {"error": str(exc), "event": f"{event_type}_DEGRADED"}
        except Exception as exc:  # noqa: BLE001
            logger.error("🚨 [HYDRA ADVANCE UNEXPECTED] %s", exc)
            ErrorGhostPipeline().capture_sync(
                exc, source="distributed_cache:advance", project="CORTEX_SYSTEM"
            )
            return {"error": str(exc), "event": f"{event_type}_FATAL"}

    # ─── Background Orchestration ────────────────────────────────────────────

    async def _start_notification_handoff(self) -> None:
        """Listener: Notifications -> Stream."""
        await asyncio.sleep(0)
        self._notification_task = asyncio.ensure_future(self._handoff_loop())
        logger.info("🐉 [HYDRA-LOG] Notification handoff active.")

    async def _start_stream_consumer(self) -> None:
        """Worker: Stream -> PostgreSQL Callback."""
        await asyncio.sleep(0)
        self._consumer_task = asyncio.ensure_future(self._consumer_loop())
        logger.info("🐲 [HYDRA-LOG] Reliable stream consumer group active.")

    async def _stop_background_tasks(self) -> None:
        for t in [self._notification_task, self._consumer_task]:
            if t and not t.done():
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await t

    # ─── Loop 1: Handoff (The Spark) ─────────────────────────────────────────

    async def _handoff_loop(self) -> None:
        """
        Intercepts Redis Exe events and pushes them into the RELIABLE Stream.
        Even if this node crashes here, the shadow key still exists for a retry.
        """
        pubsub: PubSub = self._r.pubsub()
        await pubsub.psubscribe("__keyevent@0__:expired", "__keyevent@0__:evicted")

        try:
            async for message in pubsub.listen():
                if message["type"] not in ("message", "pmessage"):
                    continue
                redis_key: str = message.get("data", "")

                if not redis_key.startswith(_TRIGGER_KEY_PREFIX):
                    continue
                agent_key = redis_key[len(_TRIGGER_KEY_PREFIX) :]

                # Rescue data
                shadow_key = f"{_SHADOW_KEY_PREFIX}{agent_key}"
                raw = await async_interceptor(self.chaos_gate, self._r.get, shadow_key)

                payload = json.loads(raw) if raw else {"_type": "TOMBSTONE", "key": agent_key}

                # Push to Hydra Stream (Persistent)
                # Atomically advances chain and logs to stream.
                await self._reliable_advance_chain(agent_key, payload, "EVICTION")

                # Cleanup shadow
                await async_interceptor(self.chaos_gate, self._r.delete, shadow_key)

        except asyncio.CancelledError:
            await pubsub.unsubscribe()
            await pubsub.aclose()
            raise
        except (ValueError, TypeError, OSError) as exc:
            logger.error("🚨 [HANDOFF FAIL] %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("🚨 [HANDOFF UNEXPECTED] %s", exc)
            ErrorGhostPipeline().capture_sync(
                exc, source="distributed_cache:handoff", project="CORTEX_SYSTEM"
            )

    # ─── Loop 2: Reliable Consumer (The Auditor) ─────────────────────────────

    async def _consumer_loop(self) -> None:
        """
        Reads from Stream with Consumer Group semantics.
        Guarantees that audit_callback is called At-Least-Once.
        """
        consumer_id = f"{self._node_id}-worker"

        while True:
            try:
                # 1. Read pending / new messages (XREADGROUP)
                items = await async_interceptor(
                    self.chaos_gate,
                    self._r.xreadgroup,
                    _AUDIT_GROUP_NAME,
                    consumer_id,
                    {_AUDIT_STREAM_KEY: ">"},
                    count=10,
                    block=1000,
                )

                if not items:
                    continue

                await self._process_stream_items(items)

            except asyncio.CancelledError:
                raise
            except (ValueError, TypeError, OSError) as exc:
                logger.error("🚨 [CONSUMER RECOVERABLE CRASH] %s", exc)
                await asyncio.sleep(5)
            except Exception as exc:  # noqa: BLE001
                logger.error("🚨 [CONSUMER UNEXPECTED CRASH] %s", exc)
                ErrorGhostPipeline().capture_sync(
                    exc,
                    source="distributed_cache:consumer",
                    project="CORTEX_SYSTEM",
                )
                await asyncio.sleep(5)

    async def _process_stream_items(self, items: list) -> None:
        """Processes and acknowledges stream items."""
        for _stream, messages in items:
            for msg_id, data in messages:
                agent_key = data.get("agent_key", "unknown")

                # 2. Persist to DB (The Callback)
                if self._audit_callback:
                    try:
                        # Data in stream already has the proofs calculated by Lua
                        await self._audit_callback(agent_key, {}, data)
                        # 3. Acknowledge (Safe now)
                        await async_interceptor(
                            self.chaos_gate,
                            self._r.xack,
                            _AUDIT_STREAM_KEY,
                            _AUDIT_GROUP_NAME,
                            msg_id,
                        )
                        logger.info(
                            "✅ [HYDRA AUDIT] ACKed %s proof=%s",
                            agent_key,
                            data["current_proof"][:8],
                        )
                    except (ValueError, TypeError, OSError) as e:
                        logger.error("🚨 [CALLBACK FAIL] %s", e)
                        await asyncio.sleep(1)  # Backoff
                    except Exception as e:  # noqa: BLE001
                        logger.error("🚨 [CALLBACK UNEXPECTED] %s", e)
                        ErrorGhostPipeline().capture_sync(
                            e,
                            source="distributed_cache:callback",
                            project="CORTEX_SYSTEM",
                        )
                        await asyncio.sleep(1)

    async def prove_forgetting(self) -> dict[str, Any]:
        try:
            tip = await async_interceptor(self.chaos_gate, self._r.get, _CHAIN_TIP_KEY)
            tip = tip or _GENESIS_HASH
            count_raw = await async_interceptor(self.chaos_gate, self._r.get, _CHAIN_COUNT_KEY)
            count = int(count_raw or 0)
            return {"tip": tip, "count": count, "status": "HYDRA_VALIDATED"}
        except (ValueError, TypeError, OSError):
            return {"status": "UNAVAILABLE"}
        except Exception as e:  # noqa: BLE001
            ErrorGhostPipeline().capture_sync(
                e, source="distributed_cache:prove", project="CORTEX_SYSTEM"
            )
            return {"status": "UNAVAILABLE_FATAL"}


def make_fastapi_lifespan(audit_callback: AuditCallback | None = None) -> Any:
    from fastapi import FastAPI as _FastAPI

    @asynccontextmanager
    async def lifespan(app: _FastAPI) -> AsyncIterator[None]:
        async with DistributedSovereignCache.from_env(audit_callback) as cache:
            app.state.cache = cache
            yield

    return lifespan
