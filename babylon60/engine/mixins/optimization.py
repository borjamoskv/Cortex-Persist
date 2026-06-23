# [C5-REAL] Exergy-Maximized
"""CORTEX Optimization Mixin - High-performance buffered writes and LRU caching.
Ω₂: Thermodynamic optimization - reduces IO wait and recomputation.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from typing import Any, ClassVar, final

import aiosqlite

from babylon60.utils.canonical import canonical_json, compute_tx_hash, now_iso
from babylon60.utils.result import Err, Ok, Result

logger = logging.getLogger("babylon60.engine.optimized")


class EvictionReason(Enum):
    """Reasons for cache purging (Ω₂)."""

    TTL = "ttl_expired"
    LRU = "lru_capacity"
    MANUAL = "manual_purge"


@final
class SovereignTLRUCache:
    """Sovereign Temporal Least Recently Used Cache (Ω₂)."""

    def __init__(
        self,
        capacity: int = 1000,
        ttl: int = 300,
        on_evict: Any | None = None,
    ):
        self.cache: dict[str, tuple[Any, float]] = {}
        self.capacity = capacity
        self.ttl = ttl
        self.order: deque[str] = deque()
        self.on_evict = on_evict

        # 🔗 Sovereign Evidence Chain (Ω₀)
        self._chain_tip = hashlib.sha256(b"CORTEX_CACHE_GENESIS").hexdigest()
        self._eviction_count = 0

    def get(self, key: str) -> Any | None:
        """Retrieve value with TTL check and lazy eviction."""
        if key in self.cache:
            val, expiry = self.cache[key]
            if time.monotonic() < expiry:
                return val
            # Lazy eviction (TTL)
            self._pop_with_proof(key, val, EvictionReason.TTL)
        return None

    def set(self, key: str, value: Any):
        """Insert value, enforcing capacity with LRU evidence."""
        if key in self.cache:
            try:
                self.order.remove(key)
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)
        elif len(self.cache) >= self.capacity:
            if self.order:
                oldest_key = self.order.popleft()
                if oldest_key in self.cache:
                    old_val, _ = self.cache.pop(oldest_key)
                    self._generate_proof(oldest_key, old_val, EvictionReason.LRU)

        self.cache[key] = (value, time.monotonic() + self.ttl)
        self.order.append(key)

    def _pop_with_proof(self, key: str, value: Any, reason: EvictionReason):
        self.cache.pop(key, None)
        try:
            self.order.remove(key)
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)
        self._generate_proof(key, value, reason)

    def _generate_proof(self, key: str, value: Any, reason: EvictionReason):
        """Computes the Evidence Chain Tip and triggers the hook."""
        self._eviction_count += 1
        prev_tip = self._chain_tip

        # Crypographic commitment to forgotten data
        v_repr = hashlib.sha256(str(value).encode()).hexdigest()
        proof_material = f"{prev_tip}|{key}|{v_repr}|{reason.value}"
        self._chain_tip = hashlib.sha256(proof_material.encode()).hexdigest()

        if self.on_evict:
            audit = {
                "eviction_id": self._eviction_count,
                "prev_proof": prev_tip,
                "current_proof": self._chain_tip,
                "reason": reason.value,
                "axiom": "Ω₂",
            }
            try:
                self.on_evict(key, value, audit)
            except Exception as e:
                logger.error("SovereignTLRUCache: Eviction hook failed: %s", e)

    def prove_forgetting(self) -> dict[str, Any]:
        """State of the evidence chain."""
        return {"tip": self._chain_tip, "count": self._eviction_count}

    @staticmethod
    def verify_proof(initial_tip: str, evidence_list: list[dict[str, Any]]) -> tuple[bool, str]:
        """Mathematically proves the chain of forgetting."""
        current_tip = initial_tip
        for entry in evidence_list:
            if entry["prev_proof"] != current_tip:
                return False, current_tip
            current_tip = entry["current_proof"]
        return True, current_tip


class OptimizationMixin:
    """Provides buffered writes and caching for the CortexEngine.
    Ω₂: Thermodynamic optimization - shared resources for 10k scale.
    """

    _executor: ClassVar[ProcessPoolExecutor | None] = None

    def __init__(self):
        self._write_buffer: asyncio.Queue = asyncio.Queue()
        self._cache = SovereignTLRUCache(capacity=2000, ttl=600, on_evict=self._on_cache_evict)
        if OptimizationMixin._executor is None:
            # Saturate all available CPU cores for maximum exergy (Ω₂)
            OptimizationMixin._executor = ProcessPoolExecutor(max_workers=os.cpu_count())
        self._buffer_task: asyncio.Task | None = None
        self._is_flushing = False

    def _on_cache_evict(self, key: str, value: Any, audit: dict[str, Any]):
        """Callback to anchor eviction proofs to the immutable ledger."""
        detail = {
            "target_key": key,
            "audit_trail": audit,
            "type": "CACHE_EVICTION_PROOF",
            "commitment": "decisional_ghost",
        }
        asyncio.create_task(self._anchor_eviction(detail))

    async def _anchor_eviction(self, detail: dict):
        """Persistent anchor for the Decisional Proof."""
        try:
            async with self.session() as conn:  # type: ignore
                await self._log_transaction(conn, "SYSTEM", "CACHE_EVICTION", detail)
        except Exception as e:
            logger.error("Failed to anchor cache eviction: %s", e)

    async def start_optimizer(self):
        """Ignite the buffered writer worker."""
        if self._buffer_task is None:
            self._buffer_task = asyncio.create_task(self._buffer_worker())
        logger.info("🚀 [OPTIMIZED] Sovereign Engine optimization active (Ω₂).")

    async def stop_optimizer(self):
        """Shutdown the optimizer and flush the buffer."""
        if self._buffer_task:
            self._is_flushing = True
            await self._write_buffer.put(None)
            await self._buffer_task
            self._buffer_task = None

        if OptimizationMixin._executor is not None:
            # Force terminate child processes to completely avoid atexit hang
            try:
                for p in OptimizationMixin._executor._processes.values():
                    p.terminate()
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)
            OptimizationMixin._executor.shutdown(wait=False, cancel_futures=True)
            OptimizationMixin._executor = None

    async def _buffer_worker(self):
        batch = []
        while not self._is_flushing:
            try:
                item = await asyncio.wait_for(self._write_buffer.get(), timeout=0.05)
                if item is None:
                    break
                batch.append(item)
                self._process_batch(batch)
            except asyncio.TimeoutError:
                self._process_batch(batch)

    def _process_batch(self, batch):
        while len(batch) < 100:
            try:
                item = self._write_buffer.get_nowait()
                if item is None:
                    break
                batch.append(item)
            except asyncio.QueueEmpty:
                break
        if batch:
            asyncio.create_task(self._flush_batch(batch))
            batch.clear()

    async def _flush_batch(self, batch: list):
        async with self.session() as conn:  # type: ignore
            await conn.execute("BEGIN IMMEDIATE")
            try:
                for future, sql, params in batch:
                    try:
                        cursor = await conn.execute(sql, params)
                        if sql.strip().upper().startswith("INSERT"):
                            future.set_result(Ok(cursor.lastrowid))
                        else:
                            future.set_result(Ok(cursor.rowcount))
                    except Exception as e:
                        future.set_result(Err(str(e)))
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                for future, _, _ in batch:
                    if not future.done():
                        future.set_result(Err(f"Batch rollback: {e}"))

    async def write_optimized(self, sql: str, params: tuple = ()) -> Result[int, str]:
        """Buffered write implementation."""
        if not sql.strip().upper().startswith("SELECT"):
            future = asyncio.get_event_loop().create_future()
            await self._write_buffer.put((future, sql, params))
            return await future

        # Fallback to standard write if it's a SELECT (though select shouldn't be here)
        async with self.session() as conn:  # type: ignore
            async with conn.execute(sql, params) as cursor:
                return Ok(cursor.rowcount)

    async def _log_transaction(
        self,
        conn: aiosqlite.Connection,
        project: str,
        action: str,
        detail: dict[str, Any],
    ) -> int:
        """Unified transaction logging with caching and batching."""
        dj = canonical_json(detail)
        ts = now_iso()

        last_hash = self._cache.get(f"last_hash_{project}")
        if not last_hash:
            async with conn.execute(
                "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
            ) as cursor:
                prev = await cursor.fetchone()
                last_hash = prev[0] if prev else "GENESIS"

        loop = asyncio.get_running_loop()
        th = await loop.run_in_executor(
            OptimizationMixin._executor, compute_tx_hash, last_hash, project, action, dj, ts
        )

        sql = (
            "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        params = (project, action, dj, last_hash, th, ts)

        res = await self.write_optimized(sql, params)
        if res.is_ok():
            tx_id = res.unwrap()
            self._cache.set(f"last_hash_{project}", th)
            return tx_id
        raise RuntimeError(f"Failed to log transaction: {res.err()}")  # type: ignore
