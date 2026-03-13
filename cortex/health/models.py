"""Health data models — scores, thresholds, snapshots.

Grade is a sealed enum. MetricSnapshot is frozen. Invalid states
are structurally impossible.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class Grade(enum.Enum):
    """Sovereign health grade — sealed, ordered, no raw strings.

    Comparison uses ordinal: Grade.SOVEREIGN > Grade.FAILED.
    Each grade carries its threshold and emoji.
    """

    SOVEREIGN = ("S", 95.0, "👑")
    EXCELLENT = ("A", 85.0, "🟢")
    GOOD = ("B", 70.0, "🔵")
    ACCEPTABLE = ("C", 55.0, "🟡")
    DEGRADED = ("D", 40.0, "🟠")
    FAILED = ("F", 0.0, "🔴")

    def __init__(self, letter: str, threshold: float, emoji: str) -> None:
        self.letter = letter
        self.threshold = threshold
        self.emoji = emoji

    def __lt__(self, other: Grade) -> bool:
        if not isinstance(other, Grade):
            return NotImplemented
        return self.threshold < other.threshold

    def __le__(self, other: Grade) -> bool:
        if not isinstance(other, Grade):
            return NotImplemented
        return self.threshold <= other.threshold

    def __gt__(self, other: Grade) -> bool:
        if not isinstance(other, Grade):
            return NotImplemented
        return self.threshold > other.threshold

    def __ge__(self, other: Grade) -> bool:
        if not isinstance(other, Grade):
            return NotImplemented
        return self.threshold >= other.threshold

    @classmethod
    def from_score(cls, score: float) -> Grade:
        """Map a 0-100 score to its corresponding grade."""
        for grade in cls:
            if score >= grade.threshold:
                return grade
        return cls.FAILED

    @classmethod
    def from_letter(cls, letter: str) -> Grade:
        """Resolve a letter ('S', 'A', ...) to a Grade enum.

        Raises ValueError on unknown letters — regression impossible.
        """
        for grade in cls:
            if grade.letter == letter:
                return grade
        valid = [g.letter for g in cls]
        raise ValueError(
            f"Unknown grade letter '{letter}', valid: {valid}"
        )

    def __repr__(self) -> str:
        return f"Grade.{self.name}({self.letter})"

    def __str__(self) -> str:
        return self.letter


@dataclass(frozen=True)
class MetricSnapshot:
    """Point-in-time measurement of a single health dimension.

    Values are normalized to [0.0, 1.0] (1.0 = perfectly healthy).
    Frozen — once created, never mutated.
    """

    name: str
    value: float
    weight: float = 1.0
    unit: str = "score"
    latency_ms: float = 0.0
    description: str = ""
    remediation: str = ""
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("MetricSnapshot.name must be non-empty")
        if not (0.0 <= self.value <= 1.0):
            object.__setattr__(
                self, "value", max(0.0, min(1.0, self.value)),
            )
        if self.weight < 0:
            raise ValueError(
                f"MetricSnapshot.weight must be >= 0, got {self.weight}"
            )

    def __repr__(self) -> str:
        return (
            f"MetricSnapshot({self.name}={self.value:.2f}, "
            f"w={self.weight})"
        )


@dataclass
class HealthScore:
    """Aggregate health index (0–100).

    Grade is a sealed ``Grade`` enum — raw strings are dead.
    """

    score: float
    grade: Grade
    metrics: list[MetricSnapshot] = field(default_factory=list)
    sub_indices: dict[str, float] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def __post_init__(self) -> None:
        self.score = max(0.0, min(100.0, self.score))
        if not isinstance(self.grade, Grade):
            raise TypeError(
                f"grade must be Grade enum, got {type(self.grade).__name__}"
            )

    @property
    def healthy(self) -> bool:
        """Not Failed (score >= 40)."""
        return self.grade > Grade.FAILED

    def to_dict(self) -> dict:
        """Serialize to dict for JSON/MCP output."""
        return {
            "score": round(self.score, 2),
            "grade": self.grade.letter,
            "healthy": self.healthy,
            "timestamp": self.timestamp,
            "metrics": [
                {
                    "name": m.name,
                    "value": round(m.value, 4),
                    "weight": m.weight,
                    "unit": m.unit,
                }
                for m in self.metrics
            ],
            "sub_indices": self.sub_indices,
        }

    def __repr__(self) -> str:
        return (
            f"HealthScore({self.score:.1f}, "
            f"grade={self.grade.letter})"
        )


@dataclass
class HealthReport:
    """Full report with score, recommendations, and raw data."""

    score: HealthScore
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trend: str = "unknown"  # "improving" | "stable" | "degrading"
    db_path: str = ""

    @property
    def is_critical(self) -> bool:
        """True if warnings exist or grade is DEGRADED/FAILED."""
        return (
            bool(self.warnings)
            or self.score.grade <= Grade.DEGRADED
        )

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "score": self.score.to_dict(),
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "trend": self.trend,
            "is_critical": self.is_critical,
            "db_path": self.db_path,
        }

    def __repr__(self) -> str:
        return (
            f"HealthReport(score={self.score.score:.1f}, "
            f"warnings={len(self.warnings)}, "
            f"recs={len(self.recommendations)})"
        )


@dataclass(frozen=True)
class HealthThresholds:
    """Centralized threshold configuration — no magic numbers.

    Change thresholds in ONE place, all surfaces respond.
    """

    critical: float = 0.3    # Below: CRITICAL warning
    degraded: float = 0.5    # Below: degraded warning
    improve: float = 0.8     # Below: improvement recommendation
    db_warn_mb: int = 500    # DB size warning
    db_crit_mb: int = 1024   # DB size critical
    wal_warn_mb: int = 10    # WAL size warning
    wal_crit_mb: int = 50    # WAL size critical
    fact_target: int = 50    # Ideal minimum active facts
    type_diversity: int = 6  # Ideal distinct fact types


class HealthSLAViolation(Exception):
    """Raised when health drops below a contracted SLA."""

    def __init__(self, score: HealthScore, target: Grade) -> None:
        self.score = score
        self.target = target
        msg = (
            f"Health SLA Violation: Expected at least {target.letter}, "
            f"but got {score.grade.letter} ({score.score:.1f}/100)"
        )
        super().__init__(msg)


@dataclass(frozen=True)
class HealthSLA:
    """Service Level Agreement for CORTEX health.
    
    Can be used by agents to demand a certain health level before
    performing risky or intensive operations.
    """

    target_grade: Grade
    enforce_sub_indices: bool = False
    
    def evaluate(self, score: HealthScore) -> None:
        """Evaluate a score against this SLA.
        
        Raises:
            HealthSLAViolation: If score is below target_grade.
        """
        if score.grade < self.target_grade:
            raise HealthSLAViolation(score, self.target_grade)
            
        if self.enforce_sub_indices and score.sub_indices:
            # If sub-index enforcement is on, ensure no sub-index
            # is independently failing below the target threshold.
            for _, val in score.sub_indices.items():
                if val < self.target_grade.threshold:
                    raise HealthSLAViolation(score, self.target_grade)
