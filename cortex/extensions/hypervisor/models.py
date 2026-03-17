"""CORTEX Hypervisor — Tenant-Facing Surface Models.

The Telescope Inversion: these are the ONLY types a tenant ever sees.
4 dataclasses. Zero internal fields. Maximum simplicity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

__all__ = ["Memory", "HealthReport", "Receipt"]


@dataclass(frozen=True)
class Memory:
    """A single unit of recalled knowledge.

    The tenant sees relevance, not cosine_similarity.
    The tenant sees source, not agent_id or consensus_score.
    """

    content: str
    relevance: float  # 0.0–1.0, normalized from internal score
    created: datetime
    source: str  # human-readable origin


@dataclass(frozen=True)
class Receipt:
    """Opaque confirmation that a memory was stored.

    The tenant gets an ID they can reference later.
    They never see tx_id, hash, or fact_id.
    """

    id: str  # Opaque, e.g. "mem_42"
    project: str
    stored_at: datetime


@dataclass(frozen=True)
class HealthReport:
    """Project health — legible, no internal metrics exposed.

    The tenant sees 'healthy' or 'degraded', not p99 latencies
    or Merkle tree depth or endocrine hormone levels.
    """

    status: Literal["healthy", "degraded", "critical"]
    memory_count: int
    last_activity: Optional[datetime]
    integrity: Literal["verified", "unverified"]
