"""
ENCB — Baseline RAG (Passive Memory Control Group)
====================================================
Minimal append-only memory system with NO epistemic governance.
No consensus, no belief revision, no Byzantine detection.
Serves as the control group for the ENCB experiment.

Nobel-Ω Vector Ξ₄ — Control Group for Falsification.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RagFact:
    """A fact in the passive RAG system: no confidence, no consensus, no revision."""

    id: int
    content: str
    fact_type: str
    tags: list[str]
    source: str
    timestamp: float
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


class BaselineRAG:
    """Append-only memory. No governance. No epistemic filtering.

    This is what most "AI memory" systems do today:
    - Store everything
    - Search by text similarity
    - No contradiction detection
    - No trust model
    - No consensus
    - No forgetting
    """

    def __init__(self) -> None:
        self._facts: list[RagFact] = []
        self._counter: int = 0

    async def store(
        self,
        content: str,
        fact_type: str = "decision",
        tags: str = "",
        source: str = "unknown",
        meta: dict[str, Any] | None = None,
    ) -> int:
        """Append a fact. No validation, no deduplication, no consensus."""
        self._counter += 1
        fact = RagFact(
            id=self._counter,
            content=content,
            fact_type=fact_type,
            tags=tags.split(",") if isinstance(tags, str) else tags,
            source=source,
            timestamp=time.time(),
            meta=meta or {},
        )
        self._facts.append(fact)
        return fact.id

    async def search(self, query: str, top_k: int = 5) -> list[RagFact]:
        """Naive substring search — no embeddings, no ranking by trust."""
        query_lower = query.lower()
        scored: list[tuple[RagFact, float]] = []

        for fact in self._facts:
            # Simple Jaccard-like overlap score
            query_words = set(query_lower.split())
            fact_words = set(fact.content.lower().split())
            intersection = query_words & fact_words
            union = query_words | fact_words
            score = len(intersection) / len(union) if union else 0.0
            scored.append((fact, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [fact for fact, _ in scored[:top_k]]

    async def recall(self, limit: int = 10) -> list[RagFact]:
        """Return most recent facts."""
        return list(reversed(self._facts[-limit:]))

    def count_contradictions_detected(self) -> int:
        """Baseline RAG cannot detect contradictions. Always 0."""
        return 0

    def count_byzantine_detected(self) -> int:
        """Baseline RAG has no trust model. Always 0."""
        return 0

    def get_entropy(self) -> float:
        """Baseline RAG doesn't measure entropy. Returns -1 (unmeasured)."""
        return -1.0

    @property
    def total_facts(self) -> int:
        return len(self._facts)

    @property
    def unique_facts(self) -> int:
        """Count unique content hashes (dedup would reduce this, but RAG doesn't dedup)."""
        return len({f.content_hash for f in self._facts})

    @property
    def duplication_ratio(self) -> float:
        """Ratio of duplicate content. High = lots of spam stored."""
        if not self._facts:
            return 0.0
        return 1.0 - (self.unique_facts / self.total_facts)
