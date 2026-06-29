# [C5-REAL] Exergy-Maximized
"""
KV Prefix Registry for SwarmManager.
Implements RadixAttention-style prefix sharing at the application level.
AX-042 compliance: eliminates system_prompt recompute per agent.
AGENTS.md Tenant Isolation: cache_key always includes tenant_id.
"""

from __future__ import annotations

from babylon60.crypto.hash_registry import cortex_hash
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1024)
def hash_prompt(system_prompt: str) -> str:
    """O(1) SHA-256 for recurring prompts (Azkartu Optimization)."""
    return cortex_hash(system_prompt.encode())


@dataclass
class PrefixSlot:
    """A shared KV prefix slot between agents of the same mission."""

    mission_id: str
    tenant_id: str
    prefix_hash: str  # sha256 of system_prompt
    prefix_tokens: int  # length of prefix
    provider_name: str  # Physical provider where the prefix resides (e.g. 'gemini', 'anthropic')
    model_name: str  # Physical model (e.g. 'gemini-1.5-pro')
    created_at: str = field(
        default_factory=lambda: datetime.fromtimestamp(
            time.monotonic(), tz=timezone.utc
        ).isoformat()
    )
    hits: int = 0  # agents that reused this slot

    @property
    def cache_key(self) -> str:
        """Tenant-scoped cache key. NEVER expose cross-tenant."""
        return hashlib.sha256(
            f"{self.tenant_id}:{self.mission_id}:{self.prefix_hash}".encode()
        ).hexdigest()


class KVPrefixRegistry:
    """
    Application-level registry for tracking and safely sharing
    KV cache slots across multiple orchestrator missions running
    in the same process, enforcing tenant isolation (AX-042).
    """

    def __init__(self) -> None:
        self._slots: dict[str, PrefixSlot] = {}  # cache_key → slot
        self._prefix_providers: dict[str, set[str]] = {}  # prefix_hash → set of provider_names
        self._savings_tokens: int = 0

    def register(
        self,
        mission_id: str,
        tenant_id: str,
        system_prompt: str,
        provider_name: str,
        model_name: str,
    ) -> PrefixSlot:
        """Registers a new prefix slot for a mission."""
        prefix_hash = hash_prompt(system_prompt)
        slot = PrefixSlot(
            mission_id=mission_id,
            tenant_id=tenant_id,
            prefix_hash=prefix_hash,
            prefix_tokens=len(system_prompt.split()),  # approx estimation
            provider_name=provider_name,
            model_name=model_name,
        )
        self._slots[slot.cache_key] = slot

        # O(1) lookup index
        if prefix_hash not in self._prefix_providers:
            self._prefix_providers[prefix_hash] = set()
        self._prefix_providers[prefix_hash].add(provider_name)

        return slot

    def get_slot(self, mission_id: str, tenant_id: str, system_prompt: str) -> PrefixSlot | None:
        """Retrieves existing slot (cache hit) or None (cache miss)."""
        prefix_hash = hash_prompt(system_prompt)
        key = cortex_hash(f"{tenant_id}:{mission_id}:{prefix_hash}".encode())
        slot = self._slots.get(key)
        if slot:
            slot.hits += 1
            self._savings_tokens += slot.prefix_tokens
        return slot

    def check_cache_affinity(self, system_prompt: str) -> list[str]:
        """Returns provider names that have an active cache for this exact prompt hash.
        O(1) Check using dict comprehension.
        """
        prefix_hash = hash_prompt(system_prompt)
        return list(self._prefix_providers.get(prefix_hash, set()))

    def exergy_report(self) -> dict[str, Any]:
        """Recovered exergy report (AX-042)."""
        return {
            "total_slots": len(self._slots),
            "total_hits": sum(s.hits for s in self._slots.values()),
            "tokens_saved": self._savings_tokens,
            "estimated_flops_saved": self._savings_tokens * 4 * 32 * 4096**2,
        }


_registry_key = "__cortex_kv_registry__"


def get_kv_registry() -> KVPrefixRegistry:
    """True singleton provider for KVPrefixRegistry."""
    import sys

    if not hasattr(sys, _registry_key):
        setattr(sys, _registry_key, KVPrefixRegistry())
    return getattr(sys, _registry_key)
