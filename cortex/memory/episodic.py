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
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from .models import CausalEpisode, SourceMetadata

logger = logging.getLogger("cortex.memory.episodic")


@dataclass()
class EpisodicFrame:
    """A single bounded moment in time before it becomes a semantic fact.

    Acts as the unit of working memory that is context-bound (includes time,
    place, active intent, and SourceMetadata).
    """

    content: str
    source: SourceMetadata
    temporal_context: str  # e.g., "During system boot", "User query on project X"
    emotional_valence: float = 0.0
    active_intent: str = ""
    timestamp: float = field(default_factory=time.time)


class EpisodicBuffer:
    """Holds recent EpisodicFrames before semantic consolidation."""

    def __init__(self, max_frames: int = 50) -> None:
        self.frames: deque[EpisodicFrame] = deque(maxlen=max_frames)

    def add_frame(self, frame: EpisodicFrame) -> None:
        """Add a frame to the episodic buffer."""
        self.frames.append(frame)

    def get_context(self) -> str:
        """Returns a formatted string of the current buffer for the LLM."""
        return "\n".join(
            f"[{time.strftime('%H:%M:%S', time.gmtime(f.timestamp))}] "
            f"({f.source.origin} - {f.temporal_context}): {f.content}"
            for f in self.frames
        )


@dataclass()
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


# ─── Causal Episode Tracer ───────────────────────────────────────────


_TRACE_DOWN_SQL = """\
WITH RECURSIVE causal_chain(id, content, fact_type, parent_decision_id, depth) AS (
    SELECT id, content, fact_type, parent_decision_id, 0
    FROM facts WHERE id = ?
    UNION ALL
    SELECT f.id, f.content, f.fact_type, f.parent_decision_id, cc.depth + 1
    FROM facts f
    JOIN causal_chain cc ON f.parent_decision_id = cc.id
    WHERE cc.depth < ?
)
SELECT id, content, fact_type, parent_decision_id, depth
FROM causal_chain ORDER BY depth ASC;
"""

_TRACE_UP_SQL = """\
WITH RECURSIVE ancestor_chain(id, content, fact_type, parent_decision_id, depth) AS (
    SELECT id, content, fact_type, parent_decision_id, 0
    FROM facts WHERE id = ?
    UNION ALL
    SELECT f.id, f.content, f.fact_type, f.parent_decision_id, ac.depth + 1
    FROM facts f
    JOIN ancestor_chain ac ON ac.parent_decision_id = f.id
    WHERE ac.depth < ?
)
SELECT id, content, fact_type, parent_decision_id, depth
FROM ancestor_chain ORDER BY depth DESC;
"""


class CausalTracer:
    """Reconstructs causal DAGs from parent_decision_id chains.

    Philosophy: Intelligence is not about isolated facts.
    It's about understanding *why* something happened.
    The Tracer walks the causal tree so the LLM sees
    the full episode, not just a single node.
    """

    MAX_DEPTH = 20

    def __init__(self, conn) -> None:
        self._conn = conn

    async def trace_episode(
        self,
        fact_id: int,
        max_depth: Optional[int] = None,
    ) -> CausalEpisode:
        """Trace the full causal DAG from a given fact.

        First walks UP to the root, then walks DOWN from root
        to capture all descendants. Returns a CausalEpisode
        with the complete chronological chain.
        """
        depth = max_depth or self.MAX_DEPTH

        # 1. Walk UP to find the root ancestor
        root_id = fact_id
        cursor = await self._conn.execute(_TRACE_UP_SQL, (fact_id, depth))
        ancestors = await cursor.fetchall()
        if ancestors:
            root_id = ancestors[0][0]  # First row = deepest ancestor

        # 2. Walk DOWN from root to get full tree
        cursor = await self._conn.execute(_TRACE_DOWN_SQL, (root_id, depth))
        rows = await cursor.fetchall()

        chain: list[dict] = []
        ghost_count = 0
        decision_count = 0
        project = ""
        max_d = 0

        for row in rows:
            fid, content, fact_type, parent_id, d = row
            chain.append(
                {
                    "id": fid,
                    "content": content[:300],
                    "fact_type": fact_type,
                    "parent_id": parent_id,
                    "depth": d,
                }
            )
            if fact_type == "ghost":
                ghost_count += 1
            elif fact_type == "decision":
                decision_count += 1
            if d > max_d:
                max_d = d

        # Fetch project from root fact
        if root_id:
            cursor = await self._conn.execute("SELECT project FROM facts WHERE id = ?", (root_id,))
            row = await cursor.fetchone()
            if row:
                project = row[0] or ""

        return CausalEpisode(
            root_fact_id=root_id,
            fact_chain=chain,
            project=project,
            depth=max_d,
            ghost_count=ghost_count,
            decision_count=decision_count,
            summary=self._build_summary(chain),
        )

    async def recall_episode(
        self,
        query: str,
        project: str = "",
        limit: int = 3,
    ) -> list[CausalEpisode]:
        """Find facts matching a query, then trace their causal episodes.

        Uses FTS5 text search to find relevant facts, then
        reconstructs the full causal DAG for each match.
        Deduplicates episodes by root_fact_id.
        """
        # Find matching facts via FTS5
        sql = "SELECT id FROM facts WHERE content LIKE ? "
        params: list = [f"%{query}%"]
        if project:
            sql += "AND project = ? "
            params.append(project)
        sql += "ORDER BY id DESC LIMIT ?"
        params.append(limit * 2)  # Over-fetch to allow dedup

        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()

        seen_roots: set[int] = set()
        episodes: list[CausalEpisode] = []

        for (fid,) in rows:
            ep = await self.trace_episode(fid)
            if ep.root_fact_id in seen_roots:
                continue
            seen_roots.add(ep.root_fact_id)
            episodes.append(ep)
            if len(episodes) >= limit:
                break

        return episodes

    @staticmethod
    def _build_summary(chain: list[dict]) -> str:
        """Build a human-readable summary of the causal chain."""
        if not chain:
            return "Empty episode."
        lines = []
        for node in chain[:15]:
            indent = "  " * node["depth"]
            marker = "🔴" if node["fact_type"] == "ghost" else "🟢"
            lines.append(f"{indent}{marker} [{node['fact_type']}] {node['content'][:80]}")
        if len(chain) > 15:
            lines.append(f"  ... and {len(chain) - 15} more nodes")
        return "\n".join(lines)
