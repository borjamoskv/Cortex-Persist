"""CORTEX — Metamemory Schema Layer: Models, Index, and Judge.

Extracted from metamemory.py for module splitting (Ω₂: LOC ≤ 500).

Components:
  - Verdict / FOKDirective: Enum-based routing decisions
  - MemoryCard: Frozen metacognitive snapshot of a single memory
  - MetamemoryStats: Aggregate health metrics
  - MetamemoryIndex: O(1) in-memory registry of MemoryCards
  - MetacognitiveJudge: Maps retrieval results → epistemic verdicts
  - detect_repair_needed / build_memory_card: Factory utilities
"""

from __future__ import annotations

import enum
import logging
import time
from datetime import datetime, timezone
from typing import Any, Final, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("cortex.memory.metamemory")

# ─── Thresholds (Ω₃: explicit, not magic) ───────────────────────────
DEFAULT_RESPOND_CONFIDENCE: Final[float] = 0.7
DEFAULT_RESPOND_EXISTENCE: Final[float] = 0.5
DEFAULT_SEARCH_CONFIDENCE: Final[float] = 0.3
DEFAULT_STALE_DAYS: Final[float] = 90.0  # 3 months without access → stale


# ─── Verdict Enum ─────────────────────────────────────────────────────


class Verdict(str, enum.Enum):
    """Metacognitive decision emitted by the judge."""

    RESPOND = "respond"  # Confidence high → answer now
    SEARCH_MORE = "search_more"  # Partial match → broaden search
    ABSTAIN = "abstain"  # Nothing reliable → say "I don't know"


class FOKDirective(str, enum.Enum):
    """Pre-retrieval routing directive based on Feeling of Knowing."""

    RETRIEVE_INTERNAL = "retrieve_internal"  # High FOK -> search memory
    RETRIEVE_WITH_VERIFICATION = "retrieve_verify"  # Med FOK  -> search but verify
    EXTERNAL_SEARCH = "external_search"  # Low FOK  -> skip internal, go to tools


# ─── Consolidation Status ────────────────────────────────────────────

ConsolidationStatus = Literal["active", "silent", "matured", "deceased", "unknown"]


# ─── MemoryCard (Frozen Metadata Snapshot) ────────────────────────────


class MemoryCard(BaseModel):
    """Metacognitive snapshot of a single memory's epistemic state.

    Every field answers a question an agent should ask before trusting
    a memory:
      - existence_probability:  "Does this memory still exist?"
      - retrieval_confidence:   "Can I retrieve it accurately?"
      - consolidation_status:   "Is it stable or in flux?"
      - repair_needed:          "Has it been contradicted or drifted?"
      - emotional_weight:       "How important is it emotionally?"
    """

    memory_id: str = Field(..., description="Unique identifier (maps to CortexFactModel.id).")
    existence_probability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="P(memory exists) — derived from success_rate × energy_level.",
    )
    retrieval_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="P(accurate retrieval) — similarity score × energy.",
    )
    last_accessed: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of last structural access.",
    )
    access_frequency: int = Field(
        default=0,
        ge=0,
        description="Absolute access count (from CMS).",
    )
    semantic_coordinates: list[float] = Field(
        default_factory=list,
        description="Embedding vector (passthrough, not copy).",
    )
    consolidation_status: ConsolidationStatus = Field(
        default="unknown",
        description="Lifecycle state: active | silent | matured | deceased | unknown.",
    )
    repair_needed: bool = Field(
        default=False,
        description="True if contradictions, drift, or stale evidence detected.",
    )
    emotional_weight: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Amplification factor from valence+arousal [0.5, 2.0].",
    )
    causal_depth: int = Field(
        default=0,
        ge=0,
        description="Depth of causal DAG ancestry. 0 = orphan, >0 = verified chain.",
    )

    model_config = ConfigDict(frozen=True)


# ─── Metamemory Stats ─────────────────────────────────────────────────


class MetamemoryStats(BaseModel):
    """Aggregate metacognitive health summary."""

    total_memories: int = 0
    mean_existence_probability: float = 0.0
    mean_retrieval_confidence: float = 0.0
    memories_needing_repair: int = 0
    stale_memories: int = 0
    deceased_memories: int = 0

    model_config = ConfigDict(frozen=True)


# ─── Metamemory Index (O(1) Lookup) ──────────────────────────────────


class MetamemoryIndex:
    """O(1) in-memory registry of MemoryCards.

    Not a persistent store — rebuilt on demand from the living
    engram population. Think of it as a cognitive "dashboard" the
    agent consults before acting.
    """

    __slots__ = ("_cards",)

    def __init__(self) -> None:
        self._cards: dict[str, MemoryCard] = {}

    # ─── Write ────────────────────────────────────────────────

    def register(self, card: MemoryCard) -> None:
        """Register or update a memory card. O(1)."""
        self._cards[card.memory_id] = card

    def register_batch(self, cards: list[MemoryCard]) -> int:
        """Register multiple cards. Returns count registered."""
        for card in cards:
            self._cards[card.memory_id] = card
        return len(cards)

    def remove(self, memory_id: str) -> bool:
        """Remove a card. Returns True if it existed."""
        return self._cards.pop(memory_id, None) is not None

    # ─── Read ─────────────────────────────────────────────────

    def introspect(self, memory_id: str) -> Optional[MemoryCard]:
        """Retrieve the metamemory card for a single memory. O(1)."""
        return self._cards.get(memory_id)

    def introspect_batch(self, memory_ids: list[str]) -> list[MemoryCard]:
        """Batch lookup. Returns cards for all found IDs."""
        return [self._cards[mid] for mid in memory_ids if mid in self._cards]

    def query_weak_memories(self, threshold: float = 0.5) -> list[MemoryCard]:
        """Return memories with retrieval_confidence below threshold.

        Sorted weakest-first for triage priority.
        """
        weak = [c for c in self._cards.values() if c.retrieval_confidence < threshold]
        weak.sort(key=lambda c: c.retrieval_confidence)
        return weak

    def needs_repair(self) -> list[MemoryCard]:
        """Return all memories flagged for repair."""
        return [c for c in self._cards.values() if c.repair_needed]

    def summary_stats(self) -> MetamemoryStats:
        """Aggregate metacognitive health metrics."""
        if not self._cards:
            return MetamemoryStats()

        cards = list(self._cards.values())
        n = len(cards)
        now = datetime.now(timezone.utc)

        return MetamemoryStats(
            total_memories=n,
            mean_existence_probability=sum(c.existence_probability for c in cards) / n,
            mean_retrieval_confidence=sum(c.retrieval_confidence for c in cards) / n,
            memories_needing_repair=sum(1 for c in cards if c.repair_needed),
            stale_memories=sum(
                1
                for c in cards
                if (now - c.last_accessed).total_seconds() > DEFAULT_STALE_DAYS * 86400
            ),
            deceased_memories=sum(1 for c in cards if c.consolidation_status == "deceased"),
        )

    @property
    def size(self) -> int:
        """Number of tracked memories."""
        return len(self._cards)

    def __len__(self) -> int:
        return len(self._cards)

    def __contains__(self, memory_id: str) -> bool:
        return memory_id in self._cards

    def __repr__(self) -> str:
        return f"MetamemoryIndex(cards={len(self._cards)})"


# ─── Repair Detection ────────────────────────────────────────────────


def detect_repair_needed(
    energy_level: float,
    success_rate: float,
    contradiction_count: int = 0,
    days_since_access: float = 0.0,
) -> bool:
    """Determine if a memory needs repair.

    Triggers:
      1. Contradictions received (consolidation conflict)
      2. Energy collapsed below survivable threshold
      3. Success rate degraded (caused downstream errors)
      4. Stale beyond threshold (no access in 90+ days)
    """
    if contradiction_count > 0:
        return True
    if energy_level < 0.1:
        return True
    if success_rate < 0.5:
        return True
    return days_since_access > DEFAULT_STALE_DAYS


# ─── MemoryCard Factory ──────────────────────────────────────────────


def build_memory_card(
    memory_id: str,
    *,
    energy_level: float = 1.0,
    success_rate: float = 1.0,
    last_accessed_ts: Optional[float] = None,
    access_count: int = 0,
    embedding: Optional[list[float]] = None,
    consolidation_status: ConsolidationStatus = "unknown",
    contradiction_count: int = 0,
    valence_multiplier: float = 1.0,
    retrieval_similarity: float = 1.0,
    causal_depth: int = 0,
) -> MemoryCard:
    """Factory that composes a MemoryCard from existing CORTEX data.

    Derivation formulas:
      existence_probability = success_rate × energy_level
      retrieval_confidence  = retrieval_similarity × energy_level
      repair_needed         = detect_repair_needed(...)
    """
    ts = last_accessed_ts or time.time()
    last_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    days_since = max(0.0, (time.time() - ts) / 86400.0)

    return MemoryCard(
        memory_id=memory_id,
        existence_probability=max(0.0, min(1.0, success_rate * energy_level)),
        retrieval_confidence=max(0.0, min(1.0, retrieval_similarity * energy_level)),
        last_accessed=last_dt,
        access_frequency=access_count,
        semantic_coordinates=embedding or [],
        consolidation_status=consolidation_status,
        repair_needed=detect_repair_needed(
            energy_level=energy_level,
            success_rate=success_rate,
            contradiction_count=contradiction_count,
            days_since_access=days_since,
        ),
        emotional_weight=max(0.0, min(2.0, valence_multiplier)),
        causal_depth=causal_depth,
    )


# ─── Metacognitive Judge ─────────────────────────────────────────────


class MetacognitiveJudge:
    """Decision engine: maps retrieval results to epistemic verdicts.

    Given a set of retrieved MemoryCards, the judge answers:
      "¿Debo responder ahora, buscar más, o decir 'no sé'?"

    All thresholds are configurable (Ω₃: no magic numbers).
    """

    __slots__ = ("_respond_confidence", "_respond_existence", "_search_confidence")

    def __init__(
        self,
        respond_confidence: float = DEFAULT_RESPOND_CONFIDENCE,
        respond_existence: float = DEFAULT_RESPOND_EXISTENCE,
        search_confidence: float = DEFAULT_SEARCH_CONFIDENCE,
    ) -> None:
        self._respond_confidence = respond_confidence
        self._respond_existence = respond_existence
        self._search_confidence = search_confidence

    def judge(self, retrieved: list[MemoryCard]) -> Verdict:
        """Emit a metacognitive verdict based on retrieved memories.

        Decision tree:
          1. No results at all → ABSTAIN
          2. All results need repair → ABSTAIN
          3. Best result above respond thresholds → RESPOND
          4. Best result in search zone → SEARCH_MORE
          5. Otherwise → ABSTAIN
        """
        if not retrieved:
            return Verdict.ABSTAIN

        usable = [c for c in retrieved if not c.repair_needed]
        if not usable:
            logger.info(
                "MetacognitiveJudge: all %d results need repair → ABSTAIN",
                len(retrieved),
            )
            return Verdict.ABSTAIN

        # Causal provenance bonus: boost confidence for causally-grounded memories
        best = max(
            usable,
            key=lambda c: c.retrieval_confidence + min(0.1, c.causal_depth * 0.02),
        )

        if (
            best.retrieval_confidence >= self._respond_confidence
            and best.existence_probability >= self._respond_existence
        ):
            logger.debug(
                "MetacognitiveJudge: RESPOND (conf=%.3f, exist=%.3f, id=%s)",
                best.retrieval_confidence,
                best.existence_probability,
                best.memory_id,
            )
            return Verdict.RESPOND

        if best.retrieval_confidence >= self._search_confidence:
            logger.debug(
                "MetacognitiveJudge: SEARCH_MORE (conf=%.3f < %.3f, id=%s)",
                best.retrieval_confidence,
                self._respond_confidence,
                best.memory_id,
            )
            return Verdict.SEARCH_MORE

        logger.info(
            "MetacognitiveJudge: ABSTAIN (best_conf=%.3f < %.3f)",
            best.retrieval_confidence,
            self._search_confidence,
        )
        return Verdict.ABSTAIN

    def judge_with_rationale(
        self,
        retrieved: list[MemoryCard],
    ) -> tuple[Verdict, dict[str, Any]]:
        """Like judge(), but returns structured rationale for audit."""
        verdict = self.judge(retrieved)
        usable = [c for c in retrieved if not c.repair_needed]
        best = max(usable, key=lambda c: c.retrieval_confidence) if usable else None

        rationale: dict[str, Any] = {
            "verdict": verdict.value,
            "total_retrieved": len(retrieved),
            "usable_count": len(usable),
            "best_confidence": best.retrieval_confidence if best else 0.0,
            "best_existence": best.existence_probability if best else 0.0,
            "best_memory_id": best.memory_id if best else None,
            "repair_flagged": len(retrieved) - len(usable),
            "thresholds": {
                "respond_confidence": self._respond_confidence,
                "respond_existence": self._respond_existence,
                "search_confidence": self._search_confidence,
            },
        }
        return verdict, rationale
