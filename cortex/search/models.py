# [C5-REAL] Exergy-Maximized

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = ["SearchResult", "SearchScope"]


@dataclass
class SearchResult:
    """A single search result with metadata."""

    fact_id: str
    content: str
    project: str
    fact_type: str
    confidence: str
    valid_from: str
    valid_until: str | None
    tags: list[str]
    created_at: str
    updated_at: str
    score: float = 0.0
    causal_gap_score: float = 0.0
    source: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    tx_id: int | None = None
    hash: str | None = None
    graph_context: dict[str, Any] | None = field(default=None)
    db_origin: str = "core"

    def to_dict(self) -> dict:
        return {
            "id": self.fact_id,
            "content": self.content,
            "project": self.project,
            "type": self.fact_type,
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "tags": self.tags,
            "score": round(self.score, 4),
            "source": self.source,
            "db_origin": self.db_origin,
        }


class SearchScope(Enum):
    """Scope for federated search queries."""

    CORE = "core"
    PERSONAL = "personal"
    COLD = "cold"
    ALL = "all"
