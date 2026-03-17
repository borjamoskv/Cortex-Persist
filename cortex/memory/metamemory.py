"""CORTEX v7+ — Metamemory: The Agent That Knows What It Knows.

Nelson & Narens (1990) framework: FOK, JOL, calibration, TOT detection.
Schema layer (Verdict, MemoryCard, etc.) lives in metamemory_schema.py.
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Final, Optional

logger = logging.getLogger("cortex.memory.metamemory")

# Re-export schema layer for backward compatibility (Ω₂: zero import breakage)
from cortex.memory.metamemory_schema import (  # noqa: E402
    ConsolidationStatus,
    FOKDirective,
    MemoryCard,
    MetacognitiveJudge,
    MetamemoryIndex,
    MetamemoryStats,
    Verdict,
    build_memory_card,
    detect_repair_needed,
)

__all__ = [
    "ConsolidationStatus",
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


_FOK_THRESHOLD: Final[float] = 0.3

_JOL_MIN_EMBEDDING_NORM: Final[float] = 0.1
_MAX_OUTCOME_HISTORY: Final[int] = 4096
_MIN_CALIBRATION_SAMPLES: Final[int] = 10
_TOT_FOK_FLOOR: Final[float] = 0.5
_TOT_FAILURE_THRESHOLD: Final[int] = 2


@dataclass(frozen=True)
class MetaJudgment:
    """Frozen metacognitive assessment of a knowledge state."""

    fok_score: float = 0.0
    jol_score: float = 0.0
    confidence: float = 0.0
    accessibility: float = 0.0
    tip_of_tongue: bool = False
    domain: str = "declarative"
    source: str = "introspect"


@dataclass(frozen=True)
class RetrievalOutcome:
    """Ground-truth record of a retrieval attempt for calibration tracking."""

    query: str = ""
    project_id: str = "default_project"
    predicted_confidence: float = 0.0
    actual_success: bool = False
    retrieval_score: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ─── Core Engine ──────────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors. O(d).

    Uses math.fsum (Shewchuk compensated summation) for O(1) error
    bound regardless of dimensionality — critical for 384–768 dim embeddings.
    """
    if len(a) != len(b) or not a:
        return 0.0
    dot = math.fsum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(math.fsum(x * x for x in a))
    norm_b = math.sqrt(math.fsum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def _embedding_norm(embedding: list[float]) -> float:
    """L2 norm of an embedding vector. O(d).

    Uses math.fsum for numerically stable accumulation.
    """
    if not embedding:
        return 0.0
    return math.sqrt(math.fsum(x * x for x in embedding))


class MetamemoryMonitor:
    """Continuous metacognitive introspection engine (pure in-memory, no I/O)."""

    __slots__ = ("_outcomes", "_query_failures", "_fok_threshold")

    def __init__(self, fok_threshold: float = _FOK_THRESHOLD) -> None:
        self._outcomes: deque[RetrievalOutcome] = deque(maxlen=_MAX_OUTCOME_HISTORY)
        self._query_failures: dict[str, list[tuple[float, float]]] = {}
        self._fok_threshold = fok_threshold

    # ─── FOK: Feeling-of-Knowing ──────────────────────────────────

    def judge_fok(
        self,
        query_embedding: list[float],
        candidate_engrams: list[Any],
        threshold: Optional[float] = None,
    ) -> MetaJudgment:
        """Evaluate Feeling-of-Knowing for a query against candidate engrams.

        Analyzes the similarity distribution of retrieved engrams to
        estimate whether knowledge exists in memory — even if the top
        match isn't perfect.

        Returns a MetaJudgment with fok_score and accessibility populated.
        """
        rho = threshold or self._fok_threshold

        if not candidate_engrams or not query_embedding:
            return MetaJudgment(fok_score=0.0, accessibility=0.0, source="fok")

        # Compute similarity for each candidate
        similarities = _compute_similarities(query_embedding, candidate_engrams)
        if not similarities:
            return MetaJudgment(fok_score=0.0, accessibility=0.0, source="fok")

        best_sim = max(similarities)
        fok = _compute_fok_score(similarities, best_sim, rho)
        accessibility = _compute_accessibility(
            best_sim,
            similarities,
            candidate_engrams,
        )

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
        """Route query based on initial FOK assessment without full retrieval."""
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
        for the requested intent.
        """
        if not candidate_skills or not intent:
            return MetaJudgment(
                fok_score=0.0,
                accessibility=0.0,
                domain="procedural",
                source="procedural_fok",
            )

        intent_terms = set(intent.lower().replace("-", " ").split())
        best_fok = _score_best_skill(intent_terms, candidate_skills)

        accessibility = min(1.0, best_fok * 1.2)
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
        scores = _compute_jol_factors(engram)
        if not scores:
            return 0.0

        weights = [0.30, 0.25, 0.15, 0.15, 0.15]
        jol = sum(s * w for s, w in zip(scores, weights, strict=True))
        return round(min(1.0, jol), 4)

    # ─── Calibration Tracking ─────────────────────────────────────

    def record_outcome(self, outcome: RetrievalOutcome) -> None:
        """Record a retrieval outcome for calibration tracking."""
        self._outcomes.append(outcome)

        if not outcome.actual_success and outcome.predicted_confidence >= _TOT_FOK_FLOOR:
            key = outcome.query
            if key not in self._query_failures:
                self._query_failures[key] = []
            self._query_failures[key].append(
                (outcome.predicted_confidence, outcome.timestamp),
            )
            # Bound per-query history (Ω₂: entropic asymmetry)
            if len(self._query_failures[key]) > 20:
                self._query_failures[key] = self._query_failures[key][-20:]

    def calibration_score(self, project_id: Optional[str] = None) -> float:
        """Compute Brier score of confidence predictions vs outcomes.

        Lower = better calibrated. Range [0.0, 1.0].
        Returns -1.0 if insufficient data.
        """
        outcomes = self._outcomes
        if project_id:
            outcomes = [o for o in self._outcomes if o.project_id == project_id]

        if len(outcomes) < _MIN_CALIBRATION_SAMPLES:
            return -1.0

        total = sum(
            (o.predicted_confidence - (1.0 if o.actual_success else 0.0)) ** 2 for o in outcomes
        )
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
        fok_judgment = self.judge_fok(query_embedding, candidate_engrams)

        jol = 0.0
        if candidate_engrams:
            jol = self.judge_jol(candidate_engrams[0])

        raw_confidence = fok_judgment.fok_score * 0.6 + jol * 0.2 + retrieval_score * 0.2
        calibration = self.calibration_score()

        if calibration >= 0:
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
        """Identify queries with persistent Tip-of-Tongue patterns."""
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

        project_ids = {o.project_id for o in self._outcomes}
        active_segments = {pid: self.calibration_score(project_id=pid) for pid in project_ids}

        successes = sum(1 for o in self._outcomes if o.actual_success)
        avg_confidence = (
            sum(o.predicted_confidence for o in self._outcomes) / total_outcomes
            if total_outcomes > 0
            else 0.0
        )

        tier = _calibration_tier(brier)
        rounded_segments = {k: round(v, 4) if v >= 0 else -1.0 for k, v in active_segments.items()}

        return {
            "brier_score": brier,
            "calibration_tier": tier,
            "segmented_brier": rounded_segments,
            "active_domains": [k for k, v in active_segments.items() if v >= 0],
            "total_outcomes": total_outcomes,
            "successes": successes,
            "failures": total_outcomes - successes,
            "success_rate": round(successes / total_outcomes, 4) if total_outcomes > 0 else 0.0,
            "avg_predicted_confidence": round(avg_confidence, 4),
            "knowledge_gaps": len(gaps),
            "tot_patterns": gaps[:10],
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


# ─── Extracted pure functions (Suntsitu: CC flattening) ──────────────


def _compute_similarities(
    query_embedding: list[float],
    candidate_engrams: list[Any],
) -> list[float]:
    """Compute cosine similarities between query and candidate embeddings."""
    similarities: list[float] = []
    for engram in candidate_engrams:
        emb = getattr(engram, "embedding", None)
        if emb:
            similarities.append(_cosine_similarity(query_embedding, emb))
    return similarities


def _compute_fok_score(
    similarities: list[float],
    best_sim: float,
    rho: float,
) -> float:
    """Derive FOK score from similarity distribution."""
    above_threshold = sum(1 for s in similarities if s >= rho)
    partial_matches = sum(1 for s in similarities if rho * 0.5 <= s < rho)

    proximity_score = min(1.0, best_sim / max(rho, 1e-9))
    distribution_score = min(
        1.0,
        (above_threshold + partial_matches * 0.5) / max(len(similarities), 1),
    )
    return 0.6 * proximity_score + 0.4 * distribution_score


def _compute_accessibility(
    best_sim: float,
    similarities: list[float],
    candidate_engrams: list[Any],
) -> float:
    """Compute accessibility factoring in energy decay."""
    accessibility = best_sim
    best_idx = similarities.index(best_sim)
    if best_idx < len(candidate_engrams):
        best_engram = candidate_engrams[best_idx]
        energy = getattr(best_engram, "energy_level", 1.0)
        if hasattr(best_engram, "compute_decay"):
            energy = best_engram.compute_decay()
        accessibility = best_sim * (0.5 + 0.5 * energy)
    return accessibility


def _score_best_skill(intent_terms: set[str], candidate_skills: list[Any]) -> float:
    """Find the best FOK score across candidate skills."""
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

        name_overlap = len(intent_terms.intersection(set(name.split())))
        name_boost = min(1.0, name_overlap / max(len(intent_terms), 1))

        score = min(1.0, jaccard + name_boost + 0.3)
        if score > best_fok:
            best_fok = score
    return best_fok


def _compute_jol_factors(engram: Any) -> list[float]:
    """Extract JOL scoring factors from an engram."""
    scores: list[float] = []

    # 1. Embedding health
    emb = getattr(engram, "embedding", None)
    if emb:
        emb_score = min(
            1.0,
            _embedding_norm(emb) / max(_JOL_MIN_EMBEDDING_NORM * 10, 1e-9),
        )
    else:
        emb_score = 0.0
    scores.append(emb_score)

    # 2. Content richness
    content = getattr(engram, "content", "")
    scores.append(min(1.0, len(content) / 200.0) if content else 0.0)

    # 3. Metadata completeness
    metadata = getattr(engram, "metadata", {})
    meta_keys = len(metadata) if isinstance(metadata, dict) else 0
    scores.append(min(1.0, meta_keys / 5.0))

    # 4. Connectivity
    refs = getattr(engram, "entangled_refs", [])
    scores.append(min(1.0, (len(refs) if refs else 0) / 3.0))

    # 5. Valence intensity
    valence = getattr(engram, "valence", None)
    if valence is not None:
        scores.append(abs(float(valence)))
    else:
        meta_valence = metadata.get("valence", 0.0) if isinstance(metadata, dict) else 0.0
        scores.append(abs(float(meta_valence)) if meta_valence else 0.3)

    return scores


def _calibration_tier(brier: float) -> str:
    """Map Brier score to a human-readable tier."""
    if brier < 0:
        return "insufficient_data"
    if brier < 0.05:
        return "excellent"
    if brier < 0.15:
        return "good"
    if brier < 0.25:
        return "fair"
    return "poor"
