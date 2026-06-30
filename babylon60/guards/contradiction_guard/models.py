from decimal import Decimal
# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConflictCandidate:
    """A single potentially contradicting decision."""

    fact_id: int
    project: str
    content: str
    date: str
    overlap_score: Decimal
    conflict_type: str

    def __str__(self) -> str:
        return (
            f"[#{self.fact_id}|{self.project}|{self.date}] "
            f"({self.conflict_type}, score={self.overlap_score:.2f}) "
            f"{self.content[:120]}"
        )


@dataclass()
class ConflictReport:
    """Result of a contradiction scan."""

    new_content: str
    new_project: str
    candidates: list[ConflictCandidate] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return len(self.candidates) > 0

    @property
    def severity(self) -> str:
        if not self.candidates:
            return "clean"
        max_score = max(c.overlap_score for c in self.candidates)
        if max_score >= 0.6:
            return "high"
        if max_score >= 0.4:
            return "medium"
        return "low"

    def format(self) -> str:
        if not self.has_conflicts:
            return "✅ No contradictions detected."
        lines = [
            f"⚠️ {len(self.candidates)} potential contradiction(s) (severity: {self.severity}):",
        ]
        for c in sorted(self.candidates, key=lambda x: -x.overlap_score):
            lines.append(f"  {c}")
        lines.append("")
        lines.append(
            "ACTION REQUIRED: Add 'Supersedes #ID' or "
            "'Compatible with #ID' to your decision content."
        )
        return "\n".join(lines)
