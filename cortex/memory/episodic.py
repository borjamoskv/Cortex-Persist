"""CORTEX v6+ — Temporal Abstraction (Episodic Day Summaries).

Strategy #9: Instead of storing every individual action,
compress an entire day/period into a structured episodic
snapshot that captures the essence.

Biological basis: Hippocampal time cells create temporal
sequences that are compressed during consolidation into
schema-compatible summaries.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("cortex.memory.episodic")


@dataclass(slots=True)
class EpisodeSummary:
    """A compressed temporal episode (e.g., one day's work)."""

    period_label: str  # "2025-02-26" or "Week 9"
    project: str
    summary: str
    key_decisions: list[str] = field(default_factory=list)
    key_learnings: list[str] = field(default_factory=list)
    errors_resolved: list[str] = field(default_factory=list)
    files_touched: list[str] = field(default_factory=list)
    engram_count: int = 0
    token_count: int = 0
    created_at: float = field(default_factory=time.time)

    @property
    def density(self) -> float:
        """Information density: items per token."""
        total_items = len(self.key_decisions) + len(self.key_learnings) + len(self.errors_resolved)
        return total_items / max(1, self.token_count)


class TemporalAbstractor:
    """Compresses time-bounded engram sets into episodic summaries."""

    def __init__(self, summarizer=None):
        self._summarizer = summarizer

    def abstract(
        self,
        engrams: list,
        period_label: str,
        project: str = "unknown",
    ) -> EpisodeSummary:
        """Compress a list of engrams into a single episodic summary."""
        if not engrams:
            return EpisodeSummary(
                period_label=period_label,
                project=project,
                summary="No activity.",
            )

        contents = [e.content for e in engrams]
        metadata_list = [getattr(e, "metadata", {}) for e in engrams]

        decisions = self._extract_by_type(engrams, "decision")
        errors = self._extract_by_type(engrams, "error")
        learnings = self._extract_by_type(engrams, "bridge")

        files: set[str] = set()
        for m in metadata_list:
            if isinstance(m, dict) and "file" in m:
                files.add(m["file"])

        if self._summarizer:
            summary = self._summarizer(contents)
        else:
            summary = self._heuristic_summary(contents, period_label, project)

        return EpisodeSummary(
            period_label=period_label,
            project=project,
            summary=summary,
            key_decisions=decisions[:10],
            key_learnings=learnings[:10],
            errors_resolved=errors[:10],
            files_touched=sorted(files)[:20],
            engram_count=len(engrams),
            token_count=max(1, len(summary) // 4),
        )

    @staticmethod
    def _extract_by_type(engrams: list, fact_type: str) -> list[str]:
        results = []
        for e in engrams:
            meta = getattr(e, "metadata", {})
            if isinstance(meta, dict) and meta.get("fact_type") == fact_type:
                results.append(e.content[:200])
            elif hasattr(e, "fact_type") and e.fact_type == fact_type:
                results.append(e.content[:200])
        return results

    @staticmethod
    def _heuristic_summary(contents: list[str], period: str, project: str) -> str:
        unique = list(dict.fromkeys(c.strip()[:100] for c in contents))
        items = unique[:15]
        bullet_list = "\n".join(f"- {item}" for item in items)
        return f"Period: {period} | Project: {project}\n{bullet_list}"
