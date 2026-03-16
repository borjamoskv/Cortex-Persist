"""CORTEX Hypervisor — Complexity Compressor.

Transforms rich internal types into simple tenant-facing models.
This is the thermal barrier: internal entropy stays inside.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from cortex.hypervisor.models import HealthReport, Memory, Receipt

if TYPE_CHECKING:
    from cortex.engine.models import Fact
    from cortex.search import SearchResult

__all__ = ["ComplexityCompressor"]

logger = logging.getLogger("cortex.hypervisor.compressor")


class ComplexityCompressor:
    """Compresses internal CORTEX types into tenant-safe outputs.

    Fact(16 fields) → Memory(4 fields)
    SearchResult(score, content, ...) → Memory(relevance, content, ...)
    ledger verification dict → HealthReport(integrity="verified")
    """

    __slots__ = ()

    @staticmethod
    def fact_to_memory(fact: Fact) -> Memory:
        """Compress a Fact into a Memory, stripping all internal fields."""
        return Memory(
            content=fact.content,
            relevance=_normalize_score(fact.consensus_score),  # type: ignore[type-error]
            created=_parse_iso(fact.created_at),
            source=fact.source or "system",
        )

    @staticmethod
    def search_result_to_memory(result: SearchResult) -> Memory:
        """Compress a SearchResult into a Memory."""
        return Memory(
            content=result.content,
            relevance=_normalize_score(result.score),
            created=_parse_iso(result.created_at) if hasattr(result, "created_at") else _now(),
            source=getattr(result, "source", None) or "search",
        )

    @staticmethod
    def to_receipt(fact_id: int, project: str) -> Receipt:
        """Create an opaque receipt from an internal fact_id."""
        return Receipt(
            id=f"mem_{fact_id}",
            project=project,
            stored_at=_now(),
        )

    @staticmethod
    def to_health_report(
        *,
        active_count: int,
        last_activity_iso: str | None,
        chain_valid: bool,
    ) -> HealthReport:
        """Compress system stats + ledger status into a HealthReport."""
        if active_count == 0:
            status = "degraded"
        elif not chain_valid:
            status = "critical"
        else:
            status = "healthy"

        return HealthReport(
            status=status,
            memory_count=active_count,
            last_activity=_parse_iso(last_activity_iso) if last_activity_iso else None,
            integrity="verified" if chain_valid else "unverified",
        )


# ── Private helpers ──────────────────────────────────────────────────


def _normalize_score(score: float | None) -> float:
    """Clamp any internal score into [0.0, 1.0]."""
    if score is None:
        return 0.0
    return max(0.0, min(1.0, float(score)))


def _parse_iso(iso_str: str | None) -> datetime:
    """Parse an ISO string, falling back to now() on failure."""
    if not iso_str:
        return _now()
    try:
        # Handle both naive and aware datetime strings
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return _now()


def _now() -> datetime:
    return datetime.now(timezone.utc)
