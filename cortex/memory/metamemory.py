"""CORTEX v7+ — Metamemory: The Agent That Knows What It Knows.

Strategy #11: A cognitive monitor that enables self-assessment of
knowledge states. Inspired by Nelson & Narens (1990) metamemory framework.

Four epistemic states:
  1. "I know this with certainty"       → high confidence, high accessibility
  2. "I think I know something about X" → high FOK, medium accessibility
  3. "I have no idea about X"           → low FOK, recognized absence
  4. "I learned this but encoded it poorly" → low JOL

Components:
  - MetaJudgment: Frozen assessment of a single query's knowledge state
  - RetrievalOutcome: Ground-truth record for calibration tracking
  - MetamemoryMonitor: Continuous introspection engine (pure logic, no I/O)
"""

from __future__ import annotations

import enum
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("cortex.memory.metamemory")

__all__ = [
    "FOKDirective",
    "MemoryCard",
    "MetacognitiveJudge",
    "MetaJudgment",
    "MetamemoryIndex",
    "MetamemoryMonitor",
    "MetamemoryStats",
    "RetrievalOutcome",
    "Verdict",
    "build_memory_card",
    "detect_repair_needed",
]

# ─── Constants ────────────────────────────────────────────────────────

# FOK threshold: below this similarity, knowledge is considered absent
_FOK_THRESHOLD: Final[float] = 0.3

# JOL minimum embedding norm to consider encoding valid
_JOL_MIN_EMBEDDING_NORM: Final[float] = 0.1

# Maximum outcome history to prevent unbounded growth (Ω₂)
_MAX_OUTCOME_HISTORY: Final[int] = 4096

# Minimum outcomes required for meaningful calibration
_MIN_CALIBRATION_SAMPLES: Final[int] = 10

# TOT detection: high FOK with repeated retrieval failure
_TOT_FOK_FLOOR: Final[float] = 0.5

# MetacognitiveJudge thresholds (Ω₃: explicit, not magic)
DEFAULT_RESPOND_CONFIDENCE: Final[float] = 0.7
DEFAULT_RESPOND_EXISTENCE: Final[float] = 0.5
DEFAULT_SEARCH_CONFIDENCE: Final[float] = 0.3
DEFAULT_STALE_DAYS: Final[float] = 90.0  # 3 months without access → stale
_TOT_FAILURE_THRESHOLD: Final[int] = 2


# ─── Models ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MetaJudgment:
    """Frozen metacognitive assessment of a knowledge state.

    Represents the agent's belief about what it knows regarding
    a specific query — before or after retrieval.
    """

    fok_score: float = 0.0
    """Feeling-of-Knowing: probability that the answer exists in memory [0, 1]."""

    jol_score: float = 0.0
    """Judgment-of-Learning: encoding quality of the best match [0, 1]."""

    confidence: float = 0.0
    """Calibrated confidence in retrieval success [0, 1]."""

    accessibility: float = 0.0
    """How retrievable the memory is right now [0, 1]."""

    tip_of_tongue: bool = False
    """True when FOK is high but retrieval failed (knowledge exists but is blocked)."""

    domain: str = "declarative"
    """Whether this applies to declarative facts or procedural skills."""

    source: str = "introspect"
    """What generated this judgment (introspect, fok, jol)."""


@dataclass(frozen=True, slots=True)
class RetrievalOutcome:
    """Ground-truth record of a retrieval attempt for calibration tracking."""

    query: str = ""
    """Original query text."""

    project_id: str = "default_project"
    """The project context for this retrieval."""

    predicted_confidence: float = 0.0
    """What the system predicted as confidence before retrieval."""

    actual_success: bool = False
    """Did retrieval produce a useful result?"""

    retrieval_score: float = 0.0
    """Similarity score of the best match found."""

    timestamp: float = field(default_factory=time.time)
    """Unix timestamp of this outcome."""


# ─── Core Engine ──────────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors. O(d)."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def _embedding_norm(embedding: list[float]) -> float:
    """L2 norm of an embedding vector. O(d)."""
    if not embedding:
        return 0.0
    return math.sqrt(sum(x * x for x in embedding))


class MetamemoryMonitor:
    """Continuous metacognitive introspection engine.

    Pure in-memory logic — no I/O, no async, no database access.
    Follows the same design philosophy as WorkingMemoryL1.

    The monitor tracks:
    - FOK (Feeling-of-Knowing): estimates whether knowledge exists
    - JOL (Judgment-of-Learning): scores encoding quality at store time
    - Calibration: Brier score comparing predictions vs outcomes
    - TOT (Tip-of-Tongue): detects high-FOK repeated-failure patterns
    """

    __slots__ = ("_outcomes", "_query_failures", "_fok_threshold")

    def __init__(self, fok_threshold: float = _FOK_THRESHOLD) -> None:
        self._outcomes: deque[RetrievalOutcome] = deque(maxlen=_MAX_OUTCOME_HISTORY)
        # Track per-query FOK failures for TOT detection: query → [(fok, timestamp)]
        self._query_failures: dict[str, list[tuple[float, float]]] = {}
        self._fok_threshold = fok_threshold

    # ─── FOK: Feeling-of-Knowing ──────────────────────────────────

    def judge_fok(
        self,
        query_embedding: list[float],
        candidate_engrams: list[Any],
        threshold: float | None = None,
    ) -> MetaJudgment:
        """Evaluate Feeling-of-Knowing for a query against candidate engrams.

        Analyzes the similarity distribution of retrieved engrams to
        estimate whether knowledge exists in memory — even if the top
        match isn't perfect.

        Returns a MetaJudgment with fok_score and accessibility populated.
        """
        rho = threshold or self._fok_threshold

        if not candidate_engrams or not query_embedding:
            return MetaJudgment(
                fok_score=0.0,
                accessibility=0.0,
                source="fok",
            )

        # Compute similarity for each candidate
        similarities: list[float] = []
        for engram in candidate_engrams:
            emb = getattr(engram, "embedding", None)
            if emb:
                sim = _cosine_similarity(query_embedding, emb)
                similarities.append(sim)

        if not similarities:
            return MetaJudgment(fok_score=0.0, accessibility=0.0, source="fok")

        best_sim = max(similarities)

        # FOK is high when:
        # 1. Best match is close to threshold (knowledge exists, maybe partially)
        # 2. Multiple candidates show moderate similarity (distributed knowledge)
        above_threshold = sum(1 for s in similarities if s >= rho)
        partial_matches = sum(1 for s in similarities if rho * 0.5 <= s < rho)

        # FOK Score: combination of best match proximity and distribution
        proximity_score = min(1.0, best_sim / max(rho, 1e-9))
        distribution_score = min(
            1.0, (above_threshold + partial_matches * 0.5) / max(len(similarities), 1)
        )
        fok = 0.6 * proximity_score + 0.4 * distribution_score

        # Accessibility: how easily the best match can be retrieved
        # High energy engram with recent access → high accessibility
        accessibility = best_sim  # Base: raw similarity
        best_engram = None
        best_idx = similarities.index(best_sim)
        if best_idx < len(candidate_engrams):
            best_engram = candidate_engrams[best_idx]

        if best_engram is not None:
            energy = getattr(best_engram, "energy_level", 1.0)
            if hasattr(best_engram, "compute_decay"):
                energy = best_engram.compute_decay()
            accessibility = best_sim * (0.5 + 0.5 * energy)

        # TOT detection: high FOK but best match below threshold
        is_tot = fok >= _TOT_FOK_FLOOR and best_sim < rho

        return MetaJudgment(
            fok_score=round(fok, 4),
            accessibility=round(accessibility, 4),
            tip_of_tongue=is_tot,
            domain="declarative",
            source="fok",
        )

    def fok_recommendation(self, fok_score: float) -> FOKDirective:
        """Route query based on initial FOK assessment without full retrieval.

        This enables the agent to say 'I don't know' or trigger external
        search tools immediately when it knows it lacks information
        (avoiding hallucinations).
        """
        if fok_score >= 0.8:
            return FOKDirective.RETRIEVE_INTERNAL
        elif fok_score >= 0.5:
            return FOKDirective.RETRIEVE_WITH_VERIFICATION
        return FOKDirective.EXTERNAL_SEARCH

    def judge_procedural_fok(
        self,
        intent: str,
        candidate_skills: list[Any],
    ) -> MetaJudgment:
        """Evaluate Feeling-of-Knowing for a procedural intent (skill routing).

        Returns high FOK if the system believes it has a valid skill
        for the requested intent. If FOK is low, the system explicitly
        knows it doesn't know how to do this (triggers TOT / unknown).
        """
        if not candidate_skills or not intent:
            return MetaJudgment(
                fok_score=0.0,
                accessibility=0.0,
                domain="procedural",
                source="procedural_fok",
            )

        intent_terms = set(intent.lower().replace("-", " ").split())

        best_fok = 0.0
        for skill in candidate_skills:
            name = getattr(skill, "name", "").lower().replace("-", " ")
            desc = getattr(skill, "description", "").lower().replace("-", " ")
            skill_terms = set(name.split() + desc.split())

            if not skill_terms:
                continue

            overlap = len(intent_terms.intersection(skill_terms))
            union = len(intent_terms.union(skill_terms))
            jaccard = overlap / max(union, 1)

            # Boost if name matches heavily
            name_overlap = len(intent_terms.intersection(set(name.split())))
            name_boost = min(1.0, name_overlap / max(len(intent_terms), 1))

            score = min(1.0, jaccard + name_boost + 0.3)  # +0.3 base for being a search result
            if score > best_fok:
                best_fok = score

        # Accessibility is boosted if we have a top match
        accessibility = min(1.0, best_fok * 1.2)
        # Tip of tongue if we feel we should know it but the match is poor
        is_tot = best_fok >= _TOT_FOK_FLOOR and best_fok < 0.6

        return MetaJudgment(
            fok_score=round(best_fok, 4),
            accessibility=round(accessibility, 4),
            tip_of_tongue=is_tot,
            domain="procedural",
            source="procedural_fok",
        )

    # ─── JOL: Judgment-of-Learning ────────────────────────────────

    def judge_jol(self, engram: Any) -> float:
        """Evaluate encoding quality of an engram at store time.

        Factors (each contributes to final score in [0, 1]):
          1. Embedding health: valid + sufficient norm
          2. Content richness: length and information density
          3. Metadata completeness: structured context present
          4. Connectivity: entangled_refs indicate integration
          5. Valence intensity: emotionally charged → better encoded

        Returns JOL score in [0.0, 1.0]. Higher = better encoded.
        """
        scores: list[float] = []

        # 1. Embedding health (0-1)
        emb = getattr(engram, "embedding", None)
        if emb:
            norm = _embedding_norm(emb)
            emb_score = min(1.0, norm / max(_JOL_MIN_EMBEDDING_NORM * 10, 1e-9))
            scores.append(emb_score)
        else:
            scores.append(0.0)

        # 2. Content richness (0-1)
        content = getattr(engram, "content", "")
        # Longer, denser content → better encoding
        # Diminishing returns above 200 chars
        content_score = min(1.0, len(content) / 200.0) if content else 0.0
        scores.append(content_score)

        # 3. Metadata completeness (0-1)
        metadata = getattr(engram, "metadata", {})
        meta_keys = len(metadata) if isinstance(metadata, dict) else 0
        meta_score = min(1.0, meta_keys / 5.0)
        scores.append(meta_score)

        # 4. Connectivity (0-1)
        refs = getattr(engram, "entangled_refs", [])
        ref_count = len(refs) if refs else 0
        connectivity_score = min(1.0, ref_count / 3.0)
        scores.append(connectivity_score)

        # 5. Valence intensity (0-1)
        # High absolute valence → stronger encoding (amygdala amplification)
        valence = getattr(engram, "valence", None)
        if valence is not None:
            valence_score = abs(float(valence))
        else:
            # Check metadata for valence info
            meta_valence = metadata.get("valence", 0.0) if isinstance(metadata, dict) else 0.0
            valence_score = abs(float(meta_valence)) if meta_valence else 0.3  # neutral default
        scores.append(valence_score)

        if not scores:
            return 0.0

        # Weighted average: embedding and content matter most
        weights = [0.30, 0.25, 0.15, 0.15, 0.15]
        jol = sum(s * w for s, w in zip(scores, weights, strict=True))
        return round(min(1.0, jol), 4)

    # ─── Calibration Tracking ─────────────────────────────────────

    def record_outcome(self, outcome: RetrievalOutcome) -> None:
        """Record a retrieval outcome for calibration tracking.

        Also updates TOT failure tracking for knowledge gap detection.
        """
        self._outcomes.append(outcome)

        # Track FOK failures for TOT detection
        if not outcome.actual_success and outcome.predicted_confidence >= _TOT_FOK_FLOOR:
            key = outcome.query
            if key not in self._query_failures:
                self._query_failures[key] = []
            self._query_failures[key].append((outcome.predicted_confidence, outcome.timestamp))

            # Bound per-query history (Ω₂: entropic asymmetry)
            if len(self._query_failures[key]) > 20:
                self._query_failures[key] = self._query_failures[key][-20:]

    def calibration_score(self, project_id: str | None = None) -> float:
        """Compute Brier score of confidence predictions vs outcomes.

        Brier Score = (1/N) * Σ(predicted - actual)²

        Lower = better calibrated. Range [0.0, 1.0].
        Returns -1.0 if insufficient data.
        """
        outcomes = self._outcomes
        if project_id:
            outcomes = [o for o in self._outcomes if o.project_id == project_id]

        if len(outcomes) < _MIN_CALIBRATION_SAMPLES:
            return -1.0

        total = 0.0
        for outcome in outcomes:
            actual = 1.0 if outcome.actual_success else 0.0
            total += (outcome.predicted_confidence - actual) ** 2

        return round(total / len(outcomes), 6)

    # ─── Full Introspection ───────────────────────────────────────

    def introspect(
        self,
        query_embedding: list[float],
        candidate_engrams: list[Any],
        retrieval_score: float = 0.0,
    ) -> MetaJudgment:
        """Full metacognitive assessment combining FOK, JOL, and calibration.

        This is the primary API for metacognitive evaluation.
        Call this AFTER retrieval to assess the quality of the result.
        """
        # 1. FOK assessment
        fok_judgment = self.judge_fok(query_embedding, candidate_engrams)

        # 2. JOL of best candidate (if available)
        jol = 0.0
        if candidate_engrams:
            # Pick the engram with highest similarity (approximately the best)
            jol = self.judge_jol(candidate_engrams[0])

        # 3. Calibrated confidence
        # Start with FOK as base, adjust with calibration history
        raw_confidence = fok_judgment.fok_score * 0.6 + jol * 0.2 + retrieval_score * 0.2
        calibration = self.calibration_score()

        if calibration >= 0:
            # If we tend to be overconfident (high Brier), dampen
            # If well-calibrated (low Brier), trust the raw score
            calibration_penalty = calibration * 0.3
            confidence = max(0.0, raw_confidence - calibration_penalty)
        else:
            confidence = raw_confidence

        confidence = min(1.0, confidence)

        return MetaJudgment(
            fok_score=fok_judgment.fok_score,
            jol_score=round(jol, 4),
            confidence=round(confidence, 4),
            accessibility=fok_judgment.accessibility,
            tip_of_tongue=fok_judgment.tip_of_tongue,
            domain="declarative",
            source="introspect",
        )

    # ─── Knowledge Gaps (TOT Pattern Detection) ───────────────────

    def knowledge_gaps(self) -> list[str]:
        """Identify queries with persistent Tip-of-Tongue patterns.

        Returns queries where:
        - FOK was high (the system believed knowledge existed)
        - But retrieval repeatedly failed
        These represent genuine knowledge gaps worth addressing.
        """
        gaps: list[str] = []
        for query, failures in self._query_failures.items():
            if len(failures) >= _TOT_FAILURE_THRESHOLD:
                avg_fok = sum(f[0] for f in failures) / len(failures)
                if avg_fok >= _TOT_FOK_FLOOR:
                    gaps.append(query)
        return gaps

    # ─── Diagnostics ──────────────────────────────────────────────

    def calibration_report(self) -> dict[str, Any]:
        """Diagnostic report of metamemory health."""
        brier = self.calibration_score()
        gaps = self.knowledge_gaps()
        total_outcomes = len(self._outcomes)

        # Segmented view (Ω₁: Multi-Scale Causality)
        project_ids = {o.project_id for o in self._outcomes}
        active_segments = {pid: self.calibration_score(project_id=pid) for pid in project_ids}

        # Outcome distribution
        successes = sum(1 for o in self._outcomes if o.actual_success)
        failures = total_outcomes - successes

        # Average predicted confidence
        avg_confidence = (
            sum(o.predicted_confidence for o in self._outcomes) / total_outcomes
            if total_outcomes > 0
            else 0.0
        )

        # Calibration quality tier
        if brier < 0:
            tier = "insufficient_data"
        elif brier < 0.05:
            tier = "excellent"
        elif brier < 0.15:
            tier = "good"
        elif brier < 0.25:
            tier = "fair"
        else:
            tier = "poor"

        rounded_segments = {k: round(v, 4) if v >= 0 else -1.0 for k, v in active_segments.items()}

        return {
            "brier_score": brier,
            "calibration_tier": tier,
            "segmented_brier": rounded_segments,
            "active_domains": [k for k, v in active_segments.items() if v >= 0],
            "total_outcomes": total_outcomes,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / total_outcomes, 4) if total_outcomes > 0 else 0.0,
            "avg_predicted_confidence": round(avg_confidence, 4),
            "knowledge_gaps": len(gaps),
            "tot_patterns": gaps[:10],  # Cap output (Ω₂)
            "tracked_queries": len(self._query_failures),
        }

    def __repr__(self) -> str:
        brier = self.calibration_score()
        brier_str = f"{brier:.4f}" if brier >= 0 else "n/a"
        return (
            f"MetamemoryMonitor(outcomes={len(self._outcomes)}, "
            f"brier={brier_str}, "
            f"knowledge_gaps={len(self.knowledge_gaps())})"
        )


# ═══════════════════════════════════════════════════════════════════════
# METAMEMORY SCHEMA LAYER — "Saber lo que sabes"
# ═══════════════════════════════════════════════════════════════════════


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

    def introspect(self, memory_id: str) -> MemoryCard | None:
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
    if days_since_access > DEFAULT_STALE_DAYS:
        return True
    return False


# ─── MemoryCard Factory ──────────────────────────────────────────────


def build_memory_card(
    memory_id: str,
    *,
    energy_level: float = 1.0,
    success_rate: float = 1.0,
    last_accessed_ts: float | None = None,
    access_count: int = 0,
    embedding: list[float] | None = None,
    consolidation_status: ConsolidationStatus = "unknown",
    contradiction_count: int = 0,
    valence_multiplier: float = 1.0,
    retrieval_similarity: float = 1.0,
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

        best = max(usable, key=lambda c: c.retrieval_confidence)

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

    def judge_with_rationale(self, retrieved: list[MemoryCard]) -> tuple[Verdict, dict[str, Any]]:
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
