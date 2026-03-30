# CORTEX Autodidact — KV-Aware Prefix Cache (AX-042)
# Apache-2.0 · (c) 2026 CORTEX Swarm

"""LRU prefix cache for identical strike deduplication.

Hashes (tx_type, action, canonical_detail_prefix) to detect
repeated MEV bundles or proof submissions. 100% prefix hit
on identical payloads; O(1) lookup via OrderedDict.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Any

from cortex.utils.canonical import canonical_json

__all__ = ["KVPrefixCache"]

logger = logging.getLogger("cortex.autodidact.kv_cache")

# Prefix window: first N bytes of canonical JSON used for key.
_PREFIX_WINDOW = 256


class KVPrefixCache:
    """Thread-safe LRU prefix cache (AX-042).

    Computes SHA-256 of (tx_type ‖ action ‖ detail_prefix) to produce
    a fixed-length key. Identical strikes resolve in O(1) without
    re-staging or re-validating.
    """

    def __init__(self, max_size: int = 4096) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # ── Public API ───────────────────────────────────────────────

    def compute_prefix(self, tx_type: str, action: str, detail: dict[str, Any]) -> str:
        """Derive a deterministic prefix key from transaction metadata.

        Uses first ``_PREFIX_WINDOW`` bytes of canonical JSON to allow
        shared prefix hits between payloads that differ only in trailing
        telemetry fields.
        """
        detail_canon = canonical_json(detail)[:_PREFIX_WINDOW]
        raw = f"{tx_type}\x00{action}\x00{detail_canon}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def hit(self, key: str) -> bool:
        """Return True if *key* is cached and promote to MRU."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return True
            self._misses += 1
            return False

    def get(self, key: str) -> str:
        """Retrieve cached tx_hash. Caller must check ``hit()`` first."""
        with self._lock:
            return self._cache[key]

    def store(self, key: str, tx_hash: str) -> None:
        """Insert *tx_hash* for *key*, evicting LRU if at capacity."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = tx_hash
                return
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                self._evictions += 1
            self._cache[key] = tx_hash

    def invalidate(self, key: str) -> bool:
        """Remove a specific key. Returns True if it existed."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Flush the entire cache."""
        with self._lock:
            self._cache.clear()

    def stats(self) -> dict[str, int | float]:
        """Return cache telemetry."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }
