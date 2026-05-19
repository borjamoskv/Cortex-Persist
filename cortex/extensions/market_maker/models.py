"""Sovereign Market Maker v1.0.0 — Data Models.

Precision first. All monetary/scoring logic explicitly uses Decimal.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto


class Verdict(Enum):
    """Execution verdict output by the opportunity scorer."""

    EXECUTE = auto()
    MONITOR = auto()
    IGNORE = auto()


class ExperimentStatus(Enum):
    """State machine for an autonomous market experiment."""

    DETECTED = auto()
    SCORED = auto()
    MVP_GENERATED = auto()
    VALIDATING = auto()
    SCALED = auto()
    KILLED = auto()


@dataclass(frozen=True)
class TrendSignal:
    """Phase 1: A raw trend signal detected in the wild."""

    topic: str
    source_count: int
    sources: list[str]
    velocity: Decimal


@dataclass(frozen=True)
class Opportunity:
    """Phase 2: A scored trend signal."""

    signal: TrendSignal
    tam_score: Decimal
    competition_score: Decimal
    advantage_score: Decimal
    ttm_score: Decimal
    total_score: Decimal
    verdict: Verdict


@dataclass(frozen=True)
class ValidationResult:
    """Phase 4: Output of simulated market validation."""

    spend: Decimal
    signups: int
    conversion_rate: Decimal
    should_scale: bool


@dataclass(frozen=True)
class MVPArtifact:
    """Phase 3: Rendered zero-click MVP."""

    html_content: str
    stripe_price_id: str | None = None


@dataclass
class Experiment:
    """The complete lifecycle tracker for a market experiment."""

    id: str
    topic: str
    status: ExperimentStatus
    opportunity: Opportunity | None = None
    mvp: MVPArtifact | None = None
    validation: ValidationResult | None = None
