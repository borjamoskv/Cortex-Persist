"""cortex-persist — Data Models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Memory"]


@dataclass
class Memory:
    """A single memory from the CORTEX API."""

    id: int
    project: str
    content: str
    type: str
    tags: list[str] = field(default_factory=list)
    confidence: str = "C3"
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_decision_id: int | None = None
    tenant_id: str = "default"
    consensus_score: float = 1.0
    valid_from: str | None = None
    valid_until: str | None = None
    tx_id: int | None = None
    created_at: str = ""
    updated_at: str = ""
    hash: str | None = None
    score: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        """Create a Memory from an API response dict."""
        return cls(
            id=data.get("id", 0),
            project=data.get("project", ""),
            content=data.get("content", ""),
            type=data.get("type", "knowledge"),
            tags=data.get("tags", []),
            confidence=data.get("confidence", "C3"),
            source=data.get("source"),
            metadata=data.get("metadata", {}),
            parent_decision_id=data.get("parent_decision_id"),
            tenant_id=data.get("tenant_id", "default"),
            consensus_score=data.get("consensus_score", 1.0),
            valid_from=data.get("valid_from"),
            valid_until=data.get("valid_until"),
            tx_id=data.get("tx_id"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            hash=data.get("hash"),
            score=data.get("score"),
        )

