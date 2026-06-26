# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""L1 Working Memory (Redis Distributed).

Volatile, token-budgeted buffer backed by Redis for multi-agent
LEGION-10k swarm environments.
"""

from __future__ import annotations

import json
import logging
import time
import typing
from typing import Any, Final

import redis

from cortex.memory.guardrails import SessionGuardrail
from cortex.memory.models import MemoryEvent

try:
    from cortex.extensions.security.tenant import get_tenant_id
except ImportError:

    def get_tenant_id() -> str:
        return "default"


__all__ = ["RedisWorkingMemoryL1"]

logger = logging.getLogger("cortex.memory.working.redis")

DEFAULT_MAX_TOKENS: Final[int] = 8192
_ACCESS_LOG_MAXLEN: Final[int] = 2048


class RedisWorkingMemoryL1:
    """Token-budgeted FIFO sliding window for short-term context backed by Redis."""

    __slots__ = ("_guardrail", "_max_tokens", "_prefix", "_redis")

    def __init__(
        self,
        redis_url: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        guardrail: SessionGuardrail | None = None,
        prefix: str = "cortex:l1:",
    ) -> None:
        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")
        self._max_tokens = max_tokens
        self._guardrail = guardrail
        self._prefix = prefix
        self._redis: typing.Any = redis.Redis.from_url(redis_url, decode_responses=True)

    def _buffer_key(self, tenant_id: str) -> str:
        return f"{self._prefix}buffer:{tenant_id}"

    def _tokens_key(self, tenant_id: str) -> str:
        return f"{self._prefix}tokens:{tenant_id}"

    def _access_log_key(self) -> str:
        return f"{self._prefix}access_log"

    def _calculate_priority(self, event: MemoryEvent) -> float:
        score = 1.0
        age_seconds = time.monotonic() - event.timestamp.timestamp()
        score += max(0.0, 1.0 - (age_seconds / 3600))
        meta_valence = event.metadata.get("valence", 0.0)
        score += abs(float(meta_valence)) * 0.5
        if event.role == "user":
            score += 0.5
        elif event.role == "system":
            score += 1.0
        return score

    def add_event(self, event: MemoryEvent) -> list[MemoryEvent]:
        tenant_id = event.tenant_id

        if self._guardrail is not None:
            if not self._guardrail.consume(event.token_count):
                msg = f"Session budget exhausted ({self._guardrail.consumed}/{self._guardrail.max_tokens} tokens)"
                raise RuntimeError(msg)

        project_id: str = event.metadata.get("project_id", tenant_id)
        now = time.monotonic()
        log_entry = json.dumps({"ts": now, "pid": f"{tenant_id}:{project_id}"})
        pipe = self._redis.pipeline()
        pipe.lpush(self._access_log_key(), log_entry)
        pipe.ltrim(self._access_log_key(), 0, _ACCESS_LOG_MAXLEN - 1)

        bkey = self._buffer_key(tenant_id)
        tkey = self._tokens_key(tenant_id)

        # Store the event
        event_dict = event.model_dump() if hasattr(event, "model_dump") else event.dict()
        # Convert datetime to string for json serialization
        event_dict["timestamp"] = event.timestamp.isoformat()

        pipe.rpush(bkey, json.dumps(event_dict))
        pipe.incrby(tkey, event.token_count)

        # Execute all initial commands in a single roundtrip
        results = pipe.execute()
        current_tokens = int(results[-1])

        overflow: list[MemoryEvent] = []

        # Check eviction
        if current_tokens > self._max_tokens:
            # We must fetch the whole buffer to apply priority eviction
            # Note: For strict O(1) we would use simple LPOP, but we keep priority logic for parity.
            buffer_data = self._redis.lrange(bkey, 0, -1)
            buffer = []
            for item in buffer_data:
                data = json.loads(item)
                import dateutil.parser

                if "timestamp" in data and isinstance(data["timestamp"], str):
                    data["timestamp"] = dateutil.parser.isoparse(data["timestamp"])
                buffer.append(MemoryEvent(**data))

            while current_tokens > self._max_tokens and buffer:
                lowest_priority = float("inf")
                evict_idx = 0
                for i, evt in enumerate(buffer):
                    p = self._calculate_priority(evt)
                    if p < lowest_priority:
                        lowest_priority = p
                        evict_idx = i

                evicted = buffer.pop(evict_idx)
                # Remove from redis buffer by removing the specific JSON string (tricky with duplicates,
                # but we'll rebuild the buffer to keep it atomic)
                current_tokens -= evicted.token_count
                overflow.append(evicted)

            # Re-write the buffer and token count
            pipe = self._redis.pipeline()
            pipe.delete(bkey)
            for evt in buffer:
                evt_dict = evt.model_dump() if hasattr(evt, "model_dump") else evt.dict()
                evt_dict["timestamp"] = evt.timestamp.isoformat()
                pipe.rpush(bkey, json.dumps(evt_dict))
            pipe.set(tkey, current_tokens)
            pipe.execute()

        if overflow:
            logger.debug(
                "L1 overflow [Tenant: %s]: evicted %d events (%d tokens freed)",
                tenant_id,
                len(overflow),
                sum(e.token_count for e in overflow),
            )

        return overflow

    def get_context(self, tenant_id: str | None = None) -> list[dict[str, str]]:
        tenant_id = tenant_id or get_tenant_id()
        bkey = self._buffer_key(tenant_id)
        buffer_data = self._redis.lrange(bkey, 0, -1)
        if not buffer_data:
            return []

        now = time.monotonic()
        seen: set[str] = set()
        result = []
        pipe = self._redis.pipeline()
        for item in buffer_data:
            data = json.loads(item)
            pid = data.get("metadata", {}).get("project_id", data.get("tenant_id"))
            if pid not in seen:
                log_entry = json.dumps({"ts": now, "pid": f"{tenant_id}:{pid}"})
                pipe.lpush(self._access_log_key(), log_entry)
                pipe.ltrim(self._access_log_key(), 0, _ACCESS_LOG_MAXLEN - 1)
                seen.add(pid)
            result.append({"role": data["role"], "content": data["content"]})
        if seen:
            pipe.execute()
        return result

    def get_access_frequency(self, project_id: str, window_seconds: float = 3600.0) -> float:
        log_data = self._redis.lrange(self._access_log_key(), 0, -1)
        if not log_data:
            return 0.0

        cutoff = time.monotonic() - window_seconds
        count = 0
        for item in log_data:
            entry = json.loads(item)
            if entry["ts"] > cutoff and entry["pid"] == project_id:
                count += 1
        return min(1.0, count / 100.0)

    def clear(self, tenant_id: str | None = None) -> list[MemoryEvent]:
        flushed: list[MemoryEvent] = []
        if tenant_id:
            bkey = self._buffer_key(tenant_id)
            tkey = self._tokens_key(tenant_id)
            buffer_data = self._redis.lrange(bkey, 0, -1)
            for item in buffer_data:
                data = json.loads(item)
                import dateutil.parser

                if "timestamp" in data and isinstance(data["timestamp"], str):
                    data["timestamp"] = dateutil.parser.isoparse(data["timestamp"])
                flushed.append(MemoryEvent(**data))
            self._redis.delete(bkey, tkey)
        else:
            keys = self._redis.keys(f"{self._prefix}buffer:*")
            for bkey in keys:
                buffer_data = self._redis.lrange(bkey, 0, -1)
                for item in buffer_data:
                    data = json.loads(item)
                    import dateutil.parser

                    if "timestamp" in data and isinstance(data["timestamp"], str):
                        data["timestamp"] = dateutil.parser.isoparse(data["timestamp"])
                    flushed.append(MemoryEvent(**data))
                tkey = bkey.replace("buffer:", "tokens:")  # pyright: ignore[reportArgumentType]
                self._redis.delete(bkey, tkey)
        return flushed

    def snapshot(self, tenant_id: str | None = None) -> dict[str, Any]:
        resolved_tenant_id = tenant_id or get_tenant_id()
        bkey = self._buffer_key(resolved_tenant_id)
        tkey = self._tokens_key(resolved_tenant_id)

        tokens = int(self._redis.get(tkey) or 0)
        buffer_data = self._redis.lrange(bkey, 0, -1)
        events = [json.loads(item) for item in buffer_data]

        return {
            "tenant_id": resolved_tenant_id,
            "tokens": tokens,
            "events": events,
        }

    def restore(self, snapshot_data: dict[str, Any], tenant_id: str | None = None) -> None:
        resolved_tenant_id = tenant_id or snapshot_data.get("tenant_id") or get_tenant_id()
        if not resolved_tenant_id:
            raise ValueError("Cannot restore: resolved tenant_id is None or empty.")

        bkey = self._buffer_key(resolved_tenant_id)
        tkey = self._tokens_key(resolved_tenant_id)

        events_data = snapshot_data.get("events", [])
        pipe = self._redis.pipeline()
        pipe.delete(bkey)
        for e_data in events_data:
            if isinstance(e_data, dict):
                pipe.rpush(bkey, json.dumps(e_data))
            else:
                pipe.rpush(
                    bkey,
                    json.dumps(
                        e_data.model_dump() if hasattr(e_data, "model_dump") else e_data.dict()
                    ),
                )

        tokens = snapshot_data.get("tokens", 0)
        pipe.set(tkey, tokens)
        pipe.execute()

    @property
    def current_tokens(self) -> int:
        tenant_id = get_tenant_id()
        tkey = self._tokens_key(tenant_id)
        return int(self._redis.get(tkey) or 0)

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    def utilization(self, tenant_id: str | None = None) -> float:
        tenant_id = tenant_id or get_tenant_id()
        if self._max_tokens == 0:
            return 0.0
        tkey = self._tokens_key(tenant_id)
        return int(self._redis.get(tkey) or 0) / self._max_tokens

    def event_count(self, tenant_id: str | None = None) -> int:
        tenant_id = tenant_id or get_tenant_id()
        bkey = self._buffer_key(tenant_id)
        return self._redis.llen(bkey)  # pyright: ignore[reportReturnType]

    def __len__(self) -> int:
        keys = self._redis.keys(f"{self._prefix}buffer:*")
        return sum(self._redis.llen(k) for k in keys)  # pyright: ignore[reportCallIssue, reportArgumentType]

    def __repr__(self) -> str:
        keys = self._redis.keys(f"{self._prefix}buffer:*")
        total_events = sum(self._redis.llen(k) for k in keys)  # pyright: ignore[reportCallIssue, reportArgumentType]
        tkeys = self._redis.keys(f"{self._prefix}tokens:*")
        total_tokens = sum(int(self._redis.get(k) or 0) for k in tkeys)  # pyright: ignore[reportCallIssue, reportArgumentType]
        return (
            f"RedisWorkingMemoryL1(tenants={len(keys)}  # pyright: ignore[reportArgumentType], events={total_events}, "
            f"tokens={total_tokens}/{self._max_tokens})"
        )
