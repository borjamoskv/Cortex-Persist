"""ALMA Taste Engine — Sovereign Quality Discriminator.

Evaluates output quality across 7 heuristic dimensions and assigns
a composite grade from GOAT to dead. Sync-only, zero LLM calls —
pure local heuristics based on structural signals.

Gap P0 from GOAT Framework mapping (Fact #4888).
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

__all__ = [
    "TasteDimension",
    "TasteVerdict",
    "TasteEngine",
    "GRADE_GOAT",
    "GRADE_STRONG",
    "GRADE_FUNCTIONAL",
    "GRADE_MEDIOCRE",
    "GRADE_DEAD",
]

# --- Grade constants ---
GRADE_GOAT = "GOAT"
GRADE_STRONG = "strong"
GRADE_FUNCTIONAL = "functional"
GRADE_MEDIOCRE = "mediocre"
GRADE_DEAD = "dead"

# --- Thresholds ---
_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (0.85, GRADE_GOAT),
    (0.70, GRADE_STRONG),
    (0.50, GRADE_FUNCTIONAL),
    (0.30, GRADE_MEDIOCRE),
]

# --- Dimension weights (taste + utility = 2x rest) ---
_DEFAULT_WEIGHTS: dict[str, float] = {
    "precision": 1.0,
    "utility": 2.0,
    "novelty": 1.0,
    "depth": 1.0,
    "robustness": 1.0,
    "reusability": 1.0,
    "taste": 2.0,
}

# --- Mediocrity signals ---
_FILLER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(en resumen|en conclusi[oó]n|como hemos visto)\b", re.IGNORECASE),
    re.compile(r"\b(in summary|in conclusion|as we have seen|to summarize)\b", re.IGNORECASE),
    re.compile(r"\b(it is worth noting|it should be noted|importantly)\b", re.IGNORECASE),
    re.compile(r"\b(cabe destacar|es importante señalar|vale la pena)\b", re.IGNORECASE),
    re.compile(r"\b(basically|essentially|fundamentally|obviously)\b", re.IGNORECASE),
)

_GENERIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(best practices|industry standard|cutting[- ]edge)\b", re.IGNORECASE),
    re.compile(r"\b(buenas pr[aá]cticas|est[aá]ndar de la industria)\b", re.IGNORECASE),
    re.compile(r"\b(leverage|synergy|paradigm shift|game[- ]changer)\b", re.IGNORECASE),
    re.compile(r"\b(holistic|robust solution|seamless)\b", re.IGNORECASE),
)

_DEPTH_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(trade-?off|tradeoff|compensaci[oó]n)\b", re.IGNORECASE),
    re.compile(r"\b(failure mode|modo de fallo|edge case)\b", re.IGNORECASE),
    re.compile(r"\b(because|ya que|debido a|dado que|since|therefore)\b", re.IGNORECASE),
    re.compile(r"\b(O\([^\)]+\)|complejidad|complexity)\b", re.IGNORECASE),
    re.compile(r"\b(constraint|restricci[oó]n|bottleneck|cuello de botella)\b", re.IGNORECASE),
)

_ACTIONABLE_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"```", re.IGNORECASE),  # Code blocks
    re.compile(r"\b(step \d|paso \d|primero|segundo|tercero)\b", re.IGNORECASE),
    re.compile(r"\b(ejecuta|run|install|deploy|create|build|mkdir)\b", re.IGNORECASE),
    re.compile(r"\b(TODO|FIXME|HACK|NEXT)\b"),
    re.compile(r"https?://", re.IGNORECASE),  # URLs = concrete references
)

_ROBUSTNESS_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(try|except|catch|error|raise|throw)\b", re.IGNORECASE),
    re.compile(r"\b(validate|sanitize|guard|assert|check)\b", re.IGNORECASE),
    re.compile(r"\b(fallback|retry|timeout|graceful)\b", re.IGNORECASE),
    re.compile(r"\b(if .+ is None|if not |unless |si no )\b", re.IGNORECASE),
)

_REUSE_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(class |def |function |interface |protocol )\b", re.IGNORECASE),
    re.compile(r"\b(abstract|generic|template|factory|builder)\b", re.IGNORECASE),
    re.compile(r"\b(API|SDK|CLI|library|module|package)\b", re.IGNORECASE),
    re.compile(r"\b(config|param|argument|option)\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class TasteDimension:
    """Score for a single quality dimension."""

    name: str
    score: float  # 0.0–1.0
    weight: float  # Contribution to composite
    signal: str  # Human-readable justification


@dataclass(frozen=True)
class TasteVerdict:
    """Complete taste evaluation result."""

    dimensions: tuple[TasteDimension, ...]
    composite_score: float  # Weighted average 0.0–1.0
    grade: str  # GOAT | strong | functional | mediocre | dead
    verdict: str  # One-line human assessment
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite_score": round(self.composite_score, 4),
            "grade": self.grade,
            "verdict": self.verdict,
            "dimensions": {
                d.name: {"score": round(d.score, 4), "signal": d.signal} for d in self.dimensions
            },
            "timestamp": self.timestamp,
        }


class TasteEngine:
    """Sovereign Quality Discriminator.

    Evaluates content across 7 heuristic dimensions using
    structural signal detection — no LLM, no external calls.
    """

    def __init__(
        self,
        weights: Optional[dict[str, float]] = None,
        grade_thresholds: Optional[list[tuple[float, str]]] = None,
    ) -> None:
        self._weights = weights or dict(_DEFAULT_WEIGHTS)
        self._thresholds = grade_thresholds or list(_GRADE_THRESHOLDS)
        # Pre-compute total weight for normalization
        self._total_weight = sum(self._weights.values())

    def evaluate(self, content: str, context: Optional[dict[str, Any]] = None) -> TasteVerdict:
        """Evaluate content quality across all taste dimensions.

        Args:
            content: The text/code to evaluate.
            context: Optional dict with keys like 'domain', 'existing_facts',
                     'user_preferences' for informed scoring.

        Returns:
            TasteVerdict with composite score, grade, and per-dimension breakdown.
        """
        ctx = context or {}

        if not content or not content.strip():
            return self._empty_verdict()

        dims = (
            self._score_precision(content, ctx),
            self._score_utility(content, ctx),
            self._score_novelty(content, ctx),
            self._score_depth(content, ctx),
            self._score_robustness(content, ctx),
            self._score_reusability(content, ctx),
            self._score_taste(content, ctx),
        )

        composite = self._composite(dims)
        grade = self._classify_grade(composite)
        verdict = self._generate_verdict(composite, grade, dims)

        return TasteVerdict(
            dimensions=dims,
            composite_score=round(composite, 4),
            grade=grade,
            verdict=verdict,
            timestamp=time.time(),
        )

    def is_mediocre(self, verdict: TasteVerdict) -> bool:
        """True if the verdict falls in mediocre or dead grade."""
        return verdict.grade in (GRADE_MEDIOCRE, GRADE_DEAD)

    def rank_ideas(
        self,
        ideas: list[str],
        context: Optional[dict[str, Any]] = None,
    ) -> list[TasteVerdict]:
        """Rank multiple ideas by taste score, highest first.

        Args:
            ideas: List of content strings to evaluate.
            context: Shared context for all evaluations.

        Returns:
            List of TasteVerdicts sorted by composite_score descending.
        """
        verdicts = [self.evaluate(idea, context) for idea in ideas]
        return sorted(verdicts, key=lambda v: v.composite_score, reverse=True)

    # --- Dimension scorers ---

    def _score_precision(self, content: str, ctx: dict[str, Any]) -> TasteDimension:
        """Precision: factual/technical correctness signals."""
        score = 0.5  # Neutral baseline
        signals: list[str] = []

        # Contradiction check: if existing_facts provided, compare
        existing = ctx.get("existing_facts", [])
        if existing:
            # Having context to validate against raises baseline
            score += 0.15
            signals.append(f"context-aware ({len(existing)} facts)")

        # Hedging language lowers precision confidence
        hedge_count = len(
            re.findall(r"\b(maybe|perhaps|might|could be|posiblemente|quizás)\b", content, re.I)
        )
        if hedge_count > 3:
            score -= 0.15
            signals.append(f"high hedging ({hedge_count})")
        elif hedge_count == 0:
            score += 0.1
            signals.append("assertive")

        # Concrete numbers/data boost precision
        data_count = len(re.findall(r"\b\d+\.?\d*\s*(%|ms|MB|GB|KB|Hz|fps|x)\b", content))
        if data_count >= 3:
            score += 0.2
            signals.append(f"data-rich ({data_count} metrics)")
        elif data_count >= 1:
            score += 0.1
            signals.append(f"some data ({data_count})")

        return TasteDimension(
            name="precision",
            score=max(0.0, min(1.0, score)),
            weight=self._weights.get("precision", 1.0),
            signal="; ".join(signals) if signals else "neutral baseline",
        )

    def _score_utility(self, content: str, ctx: dict[str, Any]) -> TasteDimension:
        """Utility: immediate actionability and executability."""
        score = 0.3  # Low baseline — prove utility
        signals: list[str] = []

        # Actionable markers
        action_hits = sum(1 for p in _ACTIONABLE_MARKERS if p.search(content))
        action_ratio = action_hits / len(_ACTIONABLE_MARKERS)
        score += action_ratio * 0.5
        if action_hits >= 3:
            signals.append(f"highly actionable ({action_hits} signals)")
        elif action_hits >= 1:
            signals.append(f"some actionability ({action_hits})")

        # Code blocks are strong utility signal
        code_blocks = len(re.findall(r"```", content))
        if code_blocks >= 4:
            score += 0.2
            signals.append(f"code-heavy ({code_blocks // 2} blocks)")
        elif code_blocks >= 2:
            score += 0.1
            signals.append("has code")

        # Length penalty for pure theory with no action
        word_count = len(content.split())
        if word_count > 500 and action_hits == 0:
            score -= 0.2
            signals.append("verbose without action")

        return TasteDimension(
            name="utility",
            score=max(0.0, min(1.0, score)),
            weight=self._weights.get("utility", 2.0),
            signal="; ".join(signals) if signals else "low actionability",
        )

    def _score_novelty(self, content: str, ctx: dict[str, Any]) -> TasteDimension:
        """Novelty: relevant newness, not noise."""
        score = 0.5  # Neutral
        signals: list[str] = []

        # Generic/filler patterns penalize novelty
        generic_hits = sum(1 for p in _GENERIC_PATTERNS if p.search(content))
        filler_hits = sum(1 for p in _FILLER_PATTERNS if p.search(content))

        if generic_hits >= 3:
            score -= 0.3
            signals.append(f"buzzword-heavy ({generic_hits})")
        elif generic_hits >= 1:
            score -= 0.1
            signals.append(f"some buzzwords ({generic_hits})")

        if filler_hits >= 3:
            score -= 0.2
            signals.append(f"filler-heavy ({filler_hits})")

        # Unique vocabulary density boosts novelty
        words = content.lower().split()
        if words:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio > 0.65:
                score += 0.2
                signals.append(f"high lexical density ({unique_ratio:.2f})")
            elif unique_ratio < 0.35:
                score -= 0.15
                signals.append(f"repetitive ({unique_ratio:.2f})")

        # Existing facts comparison (semantic distance approximation)
        existing = ctx.get("existing_facts", [])
        if existing:
            # Simple: check if content has low overlap with existing
            existing_text = " ".join(str(f) for f in existing).lower()
            existing_words = set(existing_text.split())
            content_words = set(content.lower().split())
            if existing_words:
                overlap = len(content_words & existing_words) / max(len(content_words), 1)
                novelty_boost = max(0.0, 0.3 * (1.0 - overlap))
                score += novelty_boost
                if novelty_boost > 0.15:
                    signals.append("novel vs. existing knowledge")

        return TasteDimension(
            name="novelty",
            score=max(0.0, min(1.0, score)),
            weight=self._weights.get("novelty", 1.0),
            signal="; ".join(signals) if signals else "neutral novelty",
        )

    def _score_depth(self, content: str, _ctx: dict[str, Any]) -> TasteDimension:
        """Depth: structural reasoning, trade-offs, failure modes."""
        score = 0.3  # Low baseline — depth must be proven
        signals: list[str] = []

        # Depth markers
        depth_hits = sum(1 for p in _DEPTH_MARKERS if p.search(content))
        depth_ratio = depth_hits / len(_DEPTH_MARKERS)
        score += depth_ratio * 0.5
        if depth_hits >= 4:
            signals.append(f"deep structural reasoning ({depth_hits})")
        elif depth_hits >= 2:
            signals.append(f"some depth ({depth_hits})")

        # Multi-layer structure (headers, lists)
        headers = len(re.findall(r"^#{1,4}\s", content, re.MULTILINE))
        lists = len(re.findall(r"^[\s]*[-*]\s", content, re.MULTILINE))
        if headers >= 3 and lists >= 5:
            score += 0.15
            signals.append("well-structured")
        elif headers >= 1:
            score += 0.05

        # Tables indicate comparative analysis
        tables = len(re.findall(r"\|.*\|.*\|", content))
        if tables >= 3:
            score += 0.1
            signals.append("comparative (tables)")

        return TasteDimension(
            name="depth",
            score=max(0.0, min(1.0, score)),
            weight=self._weights.get("depth", 1.0),
            signal="; ".join(signals) if signals else "shallow",
        )

    def _score_robustness(self, content: str, _ctx: dict[str, Any]) -> TasteDimension:
        """Robustness: edge case handling, error paths, validation."""
        score = 0.4  # Moderate baseline
        signals: list[str] = []

        # Robustness markers
        robust_hits = sum(1 for p in _ROBUSTNESS_MARKERS if p.search(content))
        if robust_hits >= 4:
            score += 0.4
            signals.append(f"robust ({robust_hits} defensive patterns)")
        elif robust_hits >= 2:
            score += 0.2
            signals.append(f"some defensive coding ({robust_hits})")
        elif robust_hits == 0:
            score -= 0.1
            signals.append("no error handling visible")

        # Content that acknowledges limitations
        limitation_hits = len(
            re.findall(
                r"\b(limitation|caveat|warning|caution|risk|danger|cuidado|riesgo)\b",
                content,
                re.IGNORECASE,
            )
        )
        if limitation_hits >= 2:
            score += 0.15
            signals.append("acknowledges risks")
        elif limitation_hits >= 1:
            score += 0.05

        return TasteDimension(
            name="robustness",
            score=max(0.0, min(1.0, score)),
            weight=self._weights.get("robustness", 1.0),
            signal="; ".join(signals) if signals else "moderate",
        )

    def _score_reusability(self, content: str, _ctx: dict[str, Any]) -> TasteDimension:
        """Reusability: abstraction potential, persistent asset generation."""
        score = 0.4  # Moderate baseline
        signals: list[str] = []

        # Reuse markers
        reuse_hits = sum(1 for p in _REUSE_MARKERS if p.search(content))
        if reuse_hits >= 4:
            score += 0.35
            signals.append(f"high reuse potential ({reuse_hits} abstractions)")
        elif reuse_hits >= 2:
            score += 0.15
            signals.append(f"some reuse ({reuse_hits})")

        # Parameterized content (configurable = reusable)
        param_hits = len(re.findall(r"\{[a-zA-Z_]+\}|<[a-zA-Z_]+>|\$[A-Z_]+", content))
        if param_hits >= 3:
            score += 0.15
            signals.append(f"parameterized ({param_hits})")

        # One-shot content that can't be reused
        word_count = len(content.split())
        if word_count < 30 and reuse_hits == 0:
            score -= 0.15
            signals.append("ephemeral/one-shot")

        return TasteDimension(
            name="reusability",
            score=max(0.0, min(1.0, score)),
            weight=self._weights.get("reusability", 1.0),
            signal="; ".join(signals) if signals else "moderate",
        )

    def _score_taste(self, content: str, ctx: dict[str, Any]) -> TasteDimension:
        """Taste: the 'soul' factor — identity, singularity, anti-mediocrity.

        This is the most subjective dimension. It penalizes generic outputs
        and rewards content that has a discernible point of view, structural
        originality, or domain-specific identity.
        """
        score = 0.5  # Neutral
        signals: list[str] = []

        # Anti-mediocrity: penalize buzzwords + filler combo
        generic_hits = sum(1 for p in _GENERIC_PATTERNS if p.search(content))
        filler_hits = sum(1 for p in _FILLER_PATTERNS if p.search(content))
        mediocrity_score = generic_hits + filler_hits

        if mediocrity_score >= 5:
            score -= 0.35
            signals.append(f"mediocrity detected ({mediocrity_score} signals)")
        elif mediocrity_score >= 3:
            score -= 0.15
            signals.append(f"some mediocrity ({mediocrity_score})")
        elif mediocrity_score == 0:
            score += 0.15
            signals.append("zero filler")

        # Identity: user preferences alignment
        prefs = ctx.get("user_preferences", {})
        if prefs:
            # Check if content aligns with declared preferences
            pref_keywords = [str(v).lower() for v in prefs.values() if isinstance(v, str)]
            content_lower = content.lower()
            matches = sum(1 for kw in pref_keywords if kw in content_lower)
            if pref_keywords and matches > 0:
                alignment = matches / len(pref_keywords)
                score += alignment * 0.2
                signals.append(f"preference-aligned ({matches}/{len(pref_keywords)})")

        # Singular voice: first-person assertions, concrete positions taken
        position_markers = len(
            re.findall(
                r"\b(we choose|I recommend|the answer is|la respuesta es|"
                r"elegimos|decidimos|the correct approach|el enfoque correcto)\b",
                content,
                re.IGNORECASE,
            )
        )
        if position_markers >= 2:
            score += 0.15
            signals.append("takes clear positions")
        elif position_markers >= 1:
            score += 0.05

        # Information density (Shannon-inspired approximation)
        # High entropy = high information content
        words = content.lower().split()
        if len(words) >= 20:
            unique = len(set(words))
            total = len(words)
            # Approximate entropy
            entropy_approx = 0.0
            freq: dict[str, int] = {}
            for w in words:
                freq[w] = freq.get(w, 0) + 1
            for count in freq.values():
                p = count / total
                if p > 0:
                    entropy_approx -= p * math.log2(p)

            # Normalize to 0-1 range (max entropy for N unique = log2(N))
            max_entropy = math.log2(unique) if unique > 1 else 1.0
            normalized = entropy_approx / max_entropy if max_entropy > 0 else 0.0

            if normalized > 0.85:
                score += 0.1
                signals.append(f"high info density ({normalized:.2f})")
            elif normalized < 0.5:
                score -= 0.1
                signals.append(f"low info density ({normalized:.2f})")

        return TasteDimension(
            name="taste",
            score=max(0.0, min(1.0, score)),
            weight=self._weights.get("taste", 2.0),
            signal="; ".join(signals) if signals else "neutral taste",
        )

    # --- Internal helpers ---

    def _composite(self, dims: tuple[TasteDimension, ...]) -> float:
        """Weighted average of all dimension scores."""
        if not dims or self._total_weight == 0:
            return 0.0
        weighted_sum = sum(d.score * d.weight for d in dims)
        return weighted_sum / self._total_weight

    def _classify_grade(self, composite: float) -> str:
        """Map composite score to grade label."""
        for threshold, grade in self._thresholds:
            if composite >= threshold:
                return grade
        return GRADE_DEAD

    def _generate_verdict(
        self,
        composite: float,
        grade: str,
        dims: tuple[TasteDimension, ...],
    ) -> str:
        """Generate a one-line human assessment."""
        # Find weakest and strongest dimension
        if not dims:
            return "No dimensions evaluated."

        strongest = max(dims, key=lambda d: d.score)
        weakest = min(dims, key=lambda d: d.score)

        verdicts: dict[str, str] = {
            GRADE_GOAT: f"Exceptional — strongest in {strongest.name} ({strongest.score:.2f})",
            GRADE_STRONG: (
                f"Solid output — {strongest.name} excels ({strongest.score:.2f}), "
                f"improve {weakest.name} ({weakest.score:.2f})"
            ),
            GRADE_FUNCTIONAL: (
                f"Functional but unremarkable — {weakest.name} drags ({weakest.score:.2f})"
            ),
            GRADE_MEDIOCRE: (
                f"Mediocre — lacks soul. Weakest: {weakest.name} ({weakest.score:.2f})"
            ),
            GRADE_DEAD: ("Dead output — no structural value. All dimensions below threshold."),
        }
        return verdicts.get(grade, f"Score: {composite:.2f}")

    def _empty_verdict(self) -> TasteVerdict:
        """Return verdict for empty/blank content."""
        dims = tuple(
            TasteDimension(name=name, score=0.0, weight=w, signal="empty content")
            for name, w in self._weights.items()
        )
        return TasteVerdict(
            dimensions=dims,
            composite_score=0.0,
            grade=GRADE_DEAD,
            verdict="Dead output — empty content.",
            timestamp=time.time(),
        )
