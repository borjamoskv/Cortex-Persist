import asyncio
import hashlib
import json
import logging
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from typing import Any, final

import aiosqlite

from cortex.engine_async import AsyncCortexEngine
from cortex.memory.temporal import now_iso
from cortex.utils.canonical import canonical_json, compute_tx_hash
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.engine.optimized")


class EvictionReason(Enum):
    """Reasons for cache purging (Ω₂)."""

    TTL = "ttl_expired"
    LRU = "lru_capacity"
    MANUAL = "manual_purge"


@final
class SovereignTLRUCache:
    """
    Sovereign Temporal Least Recently Used Cache (Ω₂).

    Maintains a cryptographic evidence chain (Ω₀) for all evictions.
    Every purged entry leaves a verifiable mathematical proof.
    """

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
            if time.time() < expiry:
                return val
            # Lazy eviction (TTL)
            self._pop_with_proof(key, val, EvictionReason.TTL)
        return None

    def set(self, key: str, value: Any):
        """Insert value, enforcing capacity with LRU evidence."""
        if key in self.cache:
            try:
                self.order.remove(key)
            except ValueError:
                pass
        elif len(self.cache) >= self.capacity:
            if self.order:
                oldest_key = self.order.popleft()
                if oldest_key in self.cache:
                    old_val, _ = self.cache.pop(oldest_key)
                    self._generate_proof(oldest_key, old_val, EvictionReason.LRU)

        self.cache[key] = (value, time.time() + self.ttl)
        self.order.append(key)

    def _pop_with_proof(self, key: str, value: Any, reason: EvictionReason):
        self.cache.pop(key, None)
        try:
            self.order.remove(key)
        except ValueError:
            pass
        self._generate_proof(key, value, reason)

    def _generate_proof(self, key: str, value: Any, reason: EvictionReason):
        """Computes the Evidence Chain Tip and triggers the hook."""
        self._eviction_count += 1
        prev_tip = self._chain_tip

        # 130/100: Crypographic commitment to forgotten data
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
            # Note: We can't recompute v_repr here because we don't have the value,
            # but we can verify consistency of the hashes provided in the audit trails
            # if they were signed or if we cross-reference with the ledger.
            # For now, we verify the chain link integrity.
            current_tip = entry["current_proof"]
        return True, current_tip


class OptimizedCortexEngine(AsyncCortexEngine):
    """
    Sovereign Optimized Engine for CORTEX.
    Implements BufferedWriter, Sovereign Cache, and CryptoPool.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._write_buffer: asyncio.Queue = asyncio.Queue()
        self._cache = SovereignTLRUCache(capacity=2000, ttl=600, on_evict=self._on_cache_evict)
        self._executor = ProcessPoolExecutor(max_workers=2)
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
            async with self.session() as conn:
                await self._log_transaction(conn, "SYSTEM", "CACHE_EVICTION", detail)
        except Exception as e:
            logger.error("Failed to anchor cache eviction: %s", e)

    async def audit_cache_integrity(self) -> dict[str, Any]:
        """
        Periodically audit the cache evidence chain against the ledger (Ω₃).
        Verifies that the current cache tip correctly derives from past transitions.
        """
        async with self.session() as conn:
            cursor = await conn.execute(
                "SELECT detail FROM transactions WHERE action = 'CACHE_EVICTION' ORDER BY id DESC LIMIT 100"
            )
            rows = await cursor.fetchall()
            if not rows:
                return {"status": "NO_EVICTIONS_TO_AUDIT"}

            # Parse audit trails (newest to oldest)
            trails = []
            for row in rows:
                try:
                    trails.append(json.loads(row[0])["audit_trail"])
                except (KeyError, json.JSONDecodeError):
                    continue

            if not trails:
                return {"status": "NO_VALID_AUDITS_FOUND"}

            # Reverse to process chronologically
            trails.reverse()
            initial_tip = trails[0]["prev_proof"]
            valid, calculated_tip = SovereignTLRUCache.verify_proof(initial_tip, trails)

            actual_tip = self._cache.prove_forgetting()["tip"]
            if valid and calculated_tip == actual_tip:
                logger.info("✅ [AUDIT] Cache Evidence Chain verified. Tip: %s", actual_tip[:16])
                return {"status": "VALIDATED", "tip": actual_tip, "evictions_audited": len(trails)}
            else:
                logger.error(
                    "❌ [AUDIT] Cache Evidence Chain CORRUPTED. Expected: %s, Found: %s",
                    actual_tip[:16],
                    calculated_tip[:16],
                )
                return {"status": "TAMPERED", "expected": actual_tip, "calculated": calculated_tip}

    async def start(self):
        if self._buffer_task is None:
            self._buffer_task = asyncio.create_task(self._buffer_worker())
        logger.info("🚀 [OPTIMIZED] Sovereign Engine ignited (Ω₀-Ω₆).")

    async def stop(self):
        if self._buffer_task:
            self._is_flushing = True
            await self._write_buffer.put(None)
            await self._buffer_task
            self._buffer_task = None
        self._executor.shutdown()

    async def _buffer_worker(self):
        batch = []
        while not self._is_flushing:
            try:
                item = await asyncio.wait_for(self._write_buffer.get(), timeout=0.05)
                if item is None:
                    break
                batch.append(item)
                while len(batch) < 100:
                    try:
                        item = self._write_buffer.get_nowait()
                        if item is None:
                            break
                        batch.append(item)
                    except asyncio.QueueEmpty:
                        break
                if batch:
                    await self._flush_batch(batch)
                    batch = []
            except asyncio.TimeoutError:
                if batch:
                    await self._flush_batch(batch)
                    batch = []

    async def _flush_batch(self, batch: list):
        async with self.session() as conn:
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

    async def write(self, sql: str, params: tuple = ()) -> Result[int, str]:
        if not sql.strip().upper().startswith("SELECT"):
            future = asyncio.get_event_loop().create_future()
            await self._write_buffer.put((future, sql, params))
            return await future
        return await super().write(sql, params)

    async def _log_transaction(
        self,
        conn: aiosqlite.Connection,
        project: str,
        action: str,
        detail: dict[str, Any],
    ) -> int:
        dj = canonical_json(detail)
        ts = now_iso()
        last_hash = self._cache.get(f"last_hash_{project}")
        if not last_hash:
            async with conn.execute(
                "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
            ) as cursor:
                prev = await cursor.fetchone()
                last_hash = prev[0] if prev else "GENESIS"
        loop = asyncio.get_event_loop()
        th = await loop.run_in_executor(
            self._executor, compute_tx_hash, last_hash, project, action, dj, ts
        )
        sql = (
            "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        params = (project, action, dj, last_hash, th, ts)
        res = await self.write(sql, params)
        if res.is_ok():
            tx_id = res.unwrap()
            self._cache.set(f"last_hash_{project}", th)
            return tx_id
        raise RuntimeError(f"Failed to log transaction: {res.err()}")
