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
from typing import Any


@dataclass
class PrefixSlot:
    """Un slot de KV prefix compartido entre agentes del mismo mission."""
    mission_id: str
    tenant_id: str
    prefix_hash: str          # sha256 del system_prompt
    prefix_tokens: int        # longitud del prefix
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hits: int = 0             # agentes que reutilizaron este slot

    @property
    def cache_key(self) -> str:
        """Tenant-scoped cache key. NEVER expose cross-tenant."""
        return hashlib.sha256(
            f"{self.tenant_id}:{self.mission_id}:{self.prefix_hash}".encode()
        ).hexdigest()


class KVPrefixRegistry:
    """
    Application-level prefix sharing registry.
    Capa de aplicación sobre prefix caching del servidor LLM.
    Training-free. O(1) lookup.
    """

    def __init__(self) -> None:
        self._slots: dict[str, PrefixSlot] = {}  # cache_key → slot
        self._savings_tokens: int = 0

    def register(
        self,
        mission_id: str,
        tenant_id: str,
        system_prompt: str,
    ) -> PrefixSlot:
        """Registra un nuevo prefix slot para una misión."""
        prefix_hash = hashlib.sha256(system_prompt.encode()).hexdigest()
        slot = PrefixSlot(
            mission_id=mission_id,
            tenant_id=tenant_id,
            prefix_hash=prefix_hash,
            prefix_tokens=len(system_prompt.split()),  # approx estimation
        )
        self._slots[slot.cache_key] = slot
        return slot

    def get_slot(self, mission_id: str, tenant_id: str, system_prompt: str) -> PrefixSlot | None:
        """Recupera slot existente (cache hit) o None (cache miss)."""
        prefix_hash = hashlib.sha256(system_prompt.encode()).hexdigest()
        key = hashlib.sha256(
            f"{tenant_id}:{mission_id}:{prefix_hash}".encode()
        ).hexdigest()
        slot = self._slots.get(key)
        if slot:
            slot.hits += 1
            self._savings_tokens += slot.prefix_tokens
        return slot

    def exergy_report(self) -> dict[str, Any]:
        """Informe de exergía recuperada (AX-042)."""
        return {
            "total_slots": len(self._slots),
            "total_hits": sum(s.hits for s in self._slots.values()),
            "tokens_saved": self._savings_tokens,
            "estimated_flops_saved": self._savings_tokens * 4 * 32 * 4096 ** 2,
        }
