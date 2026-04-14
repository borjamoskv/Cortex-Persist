"""
KV Prefix Registry para SwarmManager.
Implementa RadixAttention-style prefix sharing a nivel de aplicación.
AX-042 compliance: elimina recompute de system_prompt por agente.
AGENTS.md Tenant Isolation: cache_key siempre incluye tenant_id.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1024)
def hash_prompt(system_prompt: str) -> str:
    """O(1) SHA-256 para prompts recurrentes (Azkartu Optimization)."""
    return hashlib.sha256(system_prompt.encode()).hexdigest()


@dataclass
class PrefixSlot:
    """Un slot de KV prefix compartido entre agentes del mismo mission."""

    mission_id: str
    tenant_id: str
    prefix_hash: str  # sha256 del system_prompt
    prefix_tokens: int  # longitud del prefix
    provider_name: str  # Proveedor físico donde reside el prefix (EJ: 'gemini', 'anthropic')
    model_name: str  # Modelo físico (EJ: 'gemini-1.5-pro')
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hits: int = 0  # agentes que reutilizaron este slot

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
        """Registra un nuevo prefix slot para una misión."""
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
        """Recupera slot existente (cache hit) o None (cache miss)."""
        prefix_hash = hash_prompt(system_prompt)
        key = hashlib.sha256(f"{tenant_id}:{mission_id}:{prefix_hash}".encode()).hexdigest()
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
        """Informe de exergía recuperada (AX-042)."""
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
