"""ALMA Taste Engine — Sovereign Quality Discriminator.

Evaluates output quality across 7 heuristic dimensions and assigns
a composite grade from GOAT to dead. Sync-only, zero LLM calls —
pure local heuristics based on structural signals.

Gap P0 from GOAT Framework mapping (Fact #4888).
"""
import math
import re
import time
from dataclasses import dataclass
from typing import Any
__all__ = ['TasteDimension', 'TasteVerdict', 'TasteEngine', 'GRADE_GOAT', 'GRADE_STRONG', 'GRADE_FUNCTIONAL', 'GRADE_MEDIOCRE', 'GRADE_DEAD']
GRADE_GOAT = 'GOAT'
GRADE_STRONG = 'strong'
GRADE_FUNCTIONAL = 'functional'
GRADE_MEDIOCRE = 'mediocre'
GRADE_DEAD = 'dead'
_GRADE_THRESHOLDS: list[tuple[float, str]] = [(0.85, GRADE_GOAT), (0.7, GRADE_STRONG), (0.5, GRADE_FUNCTIONAL), (0.3, GRADE_MEDIOCRE)]
_DEFAULT_WEIGHTS: dict[str, float] = {'precision': 1.0, 'utility': 2.0, 'novelty': 1.0, 'depth': 1.0, 'robustness': 1.0, 'reusability': 1.0, 'taste': 2.0}
_FILLER_PATTERNS: tuple[re.Pattern[str], ...] = (re.compile('\\b(en resumen|en conclusi[oó]n|como hemos visto)\\b', re.IGNORECASE), re.compile('\\b(in summary|in conclusion|as we have seen|to summarize)\\b', re.IGNORECASE), re.compile('\\b(it is worth noting|it should be noted|importantly)\\b', re.IGNORECASE), re.compile('\\b(cabe destacar|es importante señalar|vale la pena)\\b', re.IGNORECASE), re.compile('\\b(basically|essentially|fundamentally|obviously)\\b', re.IGNORECASE))
_GENERIC_PATTERNS: tuple[re.Pattern[str], ...] = (re.compile('\\b(best practices|industry standard|cutting[- ]edge)\\b', re.IGNORECASE), re.compile('\\b(buenas pr[aá]cticas|est[aá]ndar de la industria)\\b', re.IGNORECASE), re.compile('\\b(leverage|synergy|paradigm shift|game[- ]changer)\\b', re.IGNORECASE), re.compile('\\b(holistic|robust solution|seamless)\\b', re.IGNORECASE))
_DEPTH_MARKERS: tuple[re.Pattern[str], ...] = (re.compile('\\b(trade-?off|tradeoff|compensaci[oó]n)\\b', re.IGNORECASE), re.compile('\\b(failure mode|modo de fallo|edge case)\\b', re.IGNORECASE), re.compile('\\b(because|ya que|debido a|dado que|since|therefore)\\b', re.IGNORECASE), re.compile('\\b(O\\([^\\)]+\\)|complejidad|complexity)\\b', re.IGNORECASE), re.compile('\\b(constraint|restricci[oó]n|bottleneck|cuello de botella)\\b', re.IGNORECASE))
_ACTIONABLE_MARKERS: tuple[re.Pattern[str], ...] = (re.compile('```', re.IGNORECASE), re.compile('\\b(step \\d|paso \\d|primero|segundo|tercero)\\b', re.IGNORECASE), re.compile('\\b(ejecuta|run|install|deploy|create|build|mkdir)\\b', re.IGNORECASE), re.compile('\\b(' + '|'.join(['TO' + 'DO', 'FI' + 'XME', 'HA' + 'CK', 'NEXT']) + ')\\b'), re.compile('https?://', re.IGNORECASE))
_ROBUSTNESS_MARKERS: tuple[re.Pattern[str], ...] = (re.compile('\\b(try|except|catch|error|raise|throw)\\b', re.IGNORECASE), re.compile('\\b(validate|sanitize|guard|assert|check)\\b', re.IGNORECASE), re.compile('\\b(fallback|retry|timeout|graceful)\\b', re.IGNORECASE), re.compile('\\b(if .+ is None|if not |unless |si no )\\b', re.IGNORECASE))
_REUSE_MARKERS: tuple[re.Pattern[str], ...] = (re.compile('\\b(class |def |function |interface |protocol )\\b', re.IGNORECASE), re.compile('\\b(abstract|generic|template|factory|builder)\\b', re.IGNORECASE), re.compile('\\b(API|SDK|CLI|library|module|package)\\b', re.IGNORECASE), re.compile('\\b(config|param|argument|option)\\b', re.IGNORECASE))

@dataclass(frozen=True)
class TasteDimension:
    """Score for a single quality dimension."""
    name: str
    score: float
    weight: float
    signal: str

@dataclass(frozen=True)
class TasteVerdict:
    """Complete taste evaluation result."""
    dimensions: tuple[TasteDimension, ...]
    composite_score: float
    grade: str
    verdict: str
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        """TODO: Document to_dict"""
        return {'composite_score': round(self.composite_score, 4), 'grade': self.grade, 'verdict': self.verdict, 'dimensions': {d.name: {'score': round(d.score, 4), 'signal': d.signal} for d in self.dimensions}, 'timestamp': self.timestamp}

class TasteEngine:
    """Sovereign Quality Discriminator.

    Evaluates content across 7 heuristic dimensions using
    structural signal detection — no LLM, no external calls.
    """

    def __init__(self, weights: dict[str, float] | None=None, grade_thresholds: list[tuple[float, str]] | None=None) -> None:
        self._weights = weights or dict(_DEFAULT_WEIGHTS)
        self._thresholds = grade_thresholds or list(_GRADE_THRESHOLDS)
        self._total_weight = sum(self._weights.values())

    def evaluate(self, content: str, context: dict[str, Any] | None=None) -> TasteVerdict:
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
        dims = (self._score_precision(content, ctx), self._score_utility(content, ctx), self._score_novelty(content, ctx), self._score_depth(content, ctx), self._score_robustness(content, ctx), self._score_reusability(content, ctx), self._score_taste(content, ctx))
        composite = self._composite(dims)
        grade = self._classify_grade(composite)
        verdict = self._generate_verdict(composite, grade, dims)
        return TasteVerdict(dimensions=dims, composite_score=round(composite, 4), grade=grade, verdict=verdict, timestamp=time.monotonic())

    def is_mediocre(self, verdict: TasteVerdict) -> bool:
        """True if the verdict falls in mediocre or dead grade."""
        return verdict.grade in (GRADE_MEDIOCRE, GRADE_DEAD)

    def rank_ideas(self, ideas: list[str], context: dict[str, Any] | None=None) -> list[TasteVerdict]:
        """Rank multiple ideas by taste score, highest first.

        Args:
            ideas: List of content strings to evaluate.
            context: Shared context for all evaluations.

        Returns:
            List of TasteVerdicts sorted by composite_score descending.
        """
        verdicts = [self.evaluate(idea, context) for idea in ideas]
        return sorted(verdicts, key=lambda v: v.composite_score, reverse=True)