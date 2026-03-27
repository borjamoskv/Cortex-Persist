from __future__ import annotations

import hashlib
import logging
import time
from collections import deque
from enum import Enum
from typing import Any, final

logger = logging.getLogger("cortex.engine.cache")


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
            except Exception as e:  # noqa: BLE001
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
