"""
Data models for the Contradiction Guard.

These classes encapsulate the potential conflicts found when comparing
new decisions against existing decisions in the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConflictCandidate:
    """A single potentially contradicting decision.

    Attributes:
        fact_id: The ID of the existing decision.
        project: The project context of the decision.
        content: The content snippet of the existing decision.
        date: The creation date of the existing decision.
        overlap_score: The calculated conflict severity score (0.0 to 1.0).
        conflict_type: The classification of the conflict
            ('keyword_overlap', 'negation', 'version_supersede', 'semantic_similarity').
    """

    fact_id: int
    project: str
    content: str
    date: str
    overlap_score: float
    conflict_type: str

    def __str__(self) -> str:
        """Format the conflict candidate as a human-readable string.

        Returns:
            A formatted string with conflict details.
        """
        return (
            f"[#{self.fact_id}|{self.project}|{self.date}] "
            f"({self.conflict_type}, score={self.overlap_score:.2f}) "
            f"{self.content[:120]}"
        )


@dataclass()
class ConflictReport:
    """Result of a contradiction scan.

    Attributes:
        new_content: The new decision content being evaluated.
        new_project: The project context for the new decision.
        candidates: A list of detected conflict candidates.
    """

    new_content: str
    new_project: str
    candidates: list[ConflictCandidate] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        """Check if any conflicts were detected.

        Returns:
            True if there are conflict candidates, False otherwise.
        """
        return len(self.candidates) > 0

    @property
    def severity(self) -> str:
        """Determine the maximum severity level among all candidates.

        Returns:
            'high', 'medium', 'low', or 'clean' based on the highest overlap score.
        """
        if not self.candidates:
            return "clean"
        max_score = max(c.overlap_score for c in self.candidates)
        if max_score >= 0.6:
            return "high"
        if max_score >= 0.4:
            return "medium"
        return "low"

    def format(self) -> str:
        """Format the full conflict report into a user-friendly message.

        Returns:
            A multi-line formatted string summarizing the conflicts.
        """
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
