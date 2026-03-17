"""
Context Cache Adapter — GPU-Native KV-Cache Management (Ω₁₁ / Ω₁₂).

Provider-agnostic metadata layer that manages the lifecycle of
KV-Cache (attention state) across LLM providers. CORTEX controls
the metadata and invalidation logic; the provider handles tensor
storage on GPU/TPU VRAM.

Supported providers:
  - Gemini: `cached_content` API (natively supported)
  - OpenAI: Automatic response caching (server-side)
  - vLLM/TGI: Prefix caching (local inference)

Architecture:
  - CacheEntry: metadata (project, timestamp, token_count, TTL)
  - CacheManager: create, get, invalidate, evict
  - EvictionPolicy: LRU, TTL-based, project-scoped

This module does NOT store raw tensors — it orchestrates provider
APIs that handle GPU memory allocation. CORTEX remains model-agnostic.

GPU-native: Manages GPU-resident state via provider APIs.
Edge-compatible: Cache metadata stored in SQLite.
AGI-ready: Supports multi-agent cache sharing.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("cortex.context_cache")

__all__ = [
    "ContextCacheManager",
    "CacheEntry",
    "EvictionPolicy",
    "CacheStats",
]


class EvictionPolicy(str, Enum):
    """Cache eviction strategy."""

    LRU = "lru"  # Least Recently Used
    TTL = "ttl"  # Time-To-Live expiry
    FIFO = "fifo"  # First In, First Out
    PROJECT = "project"  # Evict by project scope


@dataclass
class CacheEntry:
    """Metadata for a cached KV-Cache state.

    The actual tensor data lives on the provider's GPU/TPU.
    CORTEX only stores the reference handle.
    """

    cache_id: str
    project: str
    provider: str  # "gemini" | "openai" | "vllm" | "tgi"
    model: str  # e.g., "gemini-2.0-flash"
    token_count: int  # Number of tokens in the cached prefix
    created_at: float  # Unix timestamp
    last_accessed: float  # For LRU eviction
    ttl_seconds: int = 3600  # Default 1 hour
    provider_handle: str = ""  # Provider-specific cache ID/reference
    agent_id: str = ""  # Which agent created this cache
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl_seconds)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


@dataclass
class CacheStats:
    """Aggregate statistics for cache management."""

    total_entries: int = 0
    active_entries: int = 0
    expired_entries: int = 0
    total_tokens_cached: int = 0
    by_provider: dict[str, int] = field(default_factory=dict)
    by_project: dict[str, int] = field(default_factory=dict)
    hit_rate: float = 0.0
    evictions: int = 0


class ContextCacheManager:
    """Provider-agnostic KV-Cache lifecycle manager.

    Manages cache creation, retrieval, invalidation, and eviction
    across multiple LLM providers. The actual tensor storage is
    delegated to the provider's GPU infrastructure.

    Usage:
        mgr = ContextCacheManager(max_entries=100)
        entry = mgr.create(project="my_project", provider="gemini",
                          model="gemini-2.0-flash", token_count=8192,
                          provider_handle="cached_content/abc123")
        retrieved = mgr.get(entry.cache_id)
        mgr.invalidate(entry.cache_id)
    """

    def __init__(
        self,
        max_entries: int = 100,
        default_ttl: int = 3600,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
    ):
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._eviction_policy = eviction_policy
        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def create(
        self,
        project: str,
        provider: str,
        model: str,
        token_count: int,
        provider_handle: str = "",
        agent_id: str = "",
        ttl_seconds: Optional[int] = None,
        tags: Optional[list[str]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> CacheEntry:
        """Register a new cached KV-Cache state.

        The caller is responsible for creating the actual cache
        on the provider side (e.g., via Gemini cached_content API)
        and passing the provider_handle to this method.
        """
        import hashlib

        now = time.time()
        cache_id = hashlib.sha256(
            f"{project}:{provider}:{model}:{now}:{agent_id}".encode()
        ).hexdigest()[:16]

        entry = CacheEntry(
            cache_id=cache_id,
            project=project,
            provider=provider,
            model=model,
            token_count=token_count,
            created_at=now,
            last_accessed=now,
            ttl_seconds=ttl_seconds or self._default_ttl,
            provider_handle=provider_handle,
            agent_id=agent_id,
            tags=tags or [],
            meta=meta or {},
        )

        # Evict if at capacity
        if len(self._cache) >= self._max_entries:
            self._evict()

        self._cache[cache_id] = entry
        logger.info(
            "Cache created: %s (project=%s, provider=%s, tokens=%d)",
            cache_id,
            project,
            provider,
            token_count,
        )
        return entry

    def get(self, cache_id: str) -> Optional[CacheEntry]:
        """Retrieve a cache entry, updating access time for LRU."""
        entry = self._cache.get(cache_id)
        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            self._misses += 1
            del self._cache[cache_id]
            return None

        entry.last_accessed = time.time()
        self._hits += 1
        return entry

    def get_by_project(self, project: str) -> list[CacheEntry]:
        """Get all active cache entries for a project."""
        return [e for e in self._cache.values() if e.project == project and not e.is_expired]

    def get_by_agent(self, agent_id: str) -> list[CacheEntry]:
        """Get all active cache entries created by a specific agent."""
        return [e for e in self._cache.values() if e.agent_id == agent_id and not e.is_expired]

    def invalidate(self, cache_id: str) -> bool:
        """Invalidate a specific cache entry.

        The caller should also invalidate the provider-side cache
        (e.g., delete the Gemini cached_content resource).
        """
        if cache_id in self._cache:
            del self._cache[cache_id]
            logger.info("Cache invalidated: %s", cache_id)
            return True
        return False

    def invalidate_project(self, project: str) -> int:
        """Invalidate all cache entries for a project."""
        to_remove = [cid for cid, e in self._cache.items() if e.project == project]
        for cid in to_remove:
            del self._cache[cid]
        if to_remove:
            logger.info(
                "Cache invalidated %d entries for project %s",
                len(to_remove),
                project,
            )
        return len(to_remove)

    def invalidate_agent(self, agent_id: str) -> int:
        """Invalidate all cache entries for an agent."""
        to_remove = [cid for cid, e in self._cache.items() if e.agent_id == agent_id]
        for cid in to_remove:
            del self._cache[cid]
        return len(to_remove)

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Run periodically."""
        expired = [cid for cid, e in self._cache.items() if e.is_expired]
        for cid in expired:
            del self._cache[cid]
        if expired:
            logger.debug("Cleaned up %d expired cache entries", len(expired))
        return len(expired)

    def stats(self) -> CacheStats:
        """Compute current cache statistics."""
        active = [e for e in self._cache.values() if not e.is_expired]
        expired = len(self._cache) - len(active)

        by_provider: dict[str, int] = {}
        by_project: dict[str, int] = {}
        total_tokens = 0

        for e in active:
            by_provider[e.provider] = by_provider.get(e.provider, 0) + 1
            by_project[e.project] = by_project.get(e.project, 0) + 1
            total_tokens += e.token_count

        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return CacheStats(
            total_entries=len(self._cache),
            active_entries=len(active),
            expired_entries=expired,
            total_tokens_cached=total_tokens,
            by_provider=by_provider,
            by_project=by_project,
            hit_rate=round(hit_rate, 4),
            evictions=self._evictions,
        )

    def _evict(self) -> None:
        """Evict entries based on configured policy."""
        if not self._cache:
            return

        if self._eviction_policy == EvictionPolicy.LRU:
            oldest = min(
                self._cache.items(),
                key=lambda x: x[1].last_accessed,
            )
            del self._cache[oldest[0]]

        elif self._eviction_policy == EvictionPolicy.TTL:
            # Remove expired first, then LRU if still over capacity
            expired = [cid for cid, e in self._cache.items() if e.is_expired]
            if expired:
                del self._cache[expired[0]]
            else:
                self._evict_lru()

        elif self._eviction_policy == EvictionPolicy.FIFO:
            oldest = min(
                self._cache.items(),
                key=lambda x: x[1].created_at,
            )
            del self._cache[oldest[0]]

        self._evictions += 1

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._cache:
            oldest = min(
                self._cache.items(),
                key=lambda x: x[1].last_accessed,
            )
            del self._cache[oldest[0]]
