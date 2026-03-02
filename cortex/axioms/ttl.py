# SPDX-License-Identifier: Apache-2.0
"""Fact TTL Policy — Reconciles 'Persist Everything' with 'Entropy = Death'.

Principle: Persist aggressively. Decay intelligently.
Axioms never expire. Ghosts do.

Referenced by: AX-019 (Persist With Decay)
"""

from __future__ import annotations

# TTL in seconds. None = immortal.
FACT_TTL: dict[str, int | None] = {
    "axiom": None,              # Immutable governance — never expires
    "decision": None,           # Append-only — architecture archaeology
    "error": 90 * 86_400,       # 90 days — if not referenced, decay
    "ghost": 30 * 86_400,       # 30 days — unresolved ghosts auto-archive
    "knowledge": 180 * 86_400,  # 6 months — world knowledge degrades
    "bridge": None,             # Cross-project learning persists forever
    "meta_learning": 60 * 86_400,  # 60 days — session insights decay
    "rule": None,               # Active rules persist until revoked
    "report": None,             # Audit reports are immutable records
    "evolution": None,          # Upgrade records persist — git archaeology
    "world-model": 90 * 86_400, # 90 days — counterfactuals decay
    # ─── Types discovered in production ─────────────────────────
    "archived_ghost": 7 * 86_400,  # 7 days — already resolved, cleanup fast
    "phantom": 90 * 86_400,     # 90 days — transient observations
    "intent": 90 * 86_400,      # 90 days — session intents decay
    "research": 180 * 86_400,   # 6 months — research findings degrade
    "config": None,             # System config persists
    "schema": None,             # Schema definitions persist
}


def is_expired(fact_type: str, age_seconds: float) -> bool:
    """Check if a fact has exceeded its TTL.

    Args:
        fact_type: The canonical fact type (e.g., "ghost", "knowledge").
        age_seconds: Age of the fact in seconds since creation.

    Returns:
        True if the fact should be archived/decayed.
    """
    ttl = FACT_TTL.get(fact_type)
    if ttl is None:
        return False
    return age_seconds > ttl


def ttl_days(fact_type: str) -> int | None:
    """Return the TTL in days for a fact type, or None if immortal."""
    ttl = FACT_TTL.get(fact_type)
    if ttl is None:
        return None
    return ttl // 86_400
