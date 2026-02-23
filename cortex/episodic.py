"""
CORTEX v5.1 — Episodic Memory Engine.

Persistent native memory: stores timestamped episodic events (decisions,
errors, discoveries, flow states) across sessions, detects recurring patterns,
and provides a temporal context for the sovereign engine.

Optimized for algorithmic theme extraction without external LLM dependencies.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import TYPE_CHECKING, Any, Final

from cortex.episodic_base import (
    EMOTIONS,
    EVENT_TYPES,
    Episode,
    Pattern,
)
from cortex.temporal import now_iso

__all__ = ["EpisodicMemory"]

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.episodic")

# ─── Configuration ────────────────────────────────────────────────────

# Extended stop words for technical context filtering
_STOP_WORDS: Final[frozenset[str]] = frozenset(
    [
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "but",
        "if",
        "or",
        "because",
        "as",
        "until",
        "while",
        "of",
        "at",
        "by",
        "for",
        "with",
        "about",
        "against",
        "between",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "to",
        "from",
        "up",
        "down",
        "in",
        "out",
        "on",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "any",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "can",
        "will",
        "just",
        "should",
        "now",
        "actually",
        "basically",
        "trying",
        "fixed",
        "error",
        "issue",
        "problem",
        "failed",
        "success",
        "resolved",
        "added",
        "removed",
    ]
)

# Token extraction: Alphanumeric + underscores + hyphens (for code/technical IDs)
_TOKEN_RE: Final[re.Pattern] = re.compile(r"\b[a-z0-9_\-]{4,}\b", re.IGNORECASE)


# ─── Episodic Memory Engine ─────────────────────────────────────────


class EpisodicMemory:
    """
    Persistent episodic memory for cross-session learning.
    Analyzes temporal patterns to provide long-term "Sovereign" intuition.
    """

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def record(
        self,
        session_id: str,
        event_type: str,
        content: str,
        project: str | None = None,
        emotion: str = "neutral",
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> int:
        """Store an episodic event with cryptographic intent."""
        if event_type not in EVENT_TYPES:
            event_type = "insight"
        if emotion not in EMOTIONS:
            emotion = "neutral"

        now = now_iso()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})

        sql = """
            INSERT INTO episodes (
                session_id, event_type, content, project, emotion, tags, meta, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        async with self._conn.execute(
            sql, (session_id, event_type, content, project, emotion, tags_json, meta_json, now)
        ) as cursor:
            rowid = cursor.lastrowid or 0

        # Update FTS index (asynchronous)
        await self._conn.execute(
            "INSERT INTO episodes_fts(rowid, content) VALUES (?, ?)", (rowid, content)
        )
        return rowid

    async def recall(
        self,
        project: str | None = None,
        event_type: str | None = None,
        since: str | None = None,
        limit: int = 20,
        search: str | None = None,
    ) -> list[Episode]:
        """Retrieve episodes with multi-dimensional filtering."""
        if search:
            return await self._fts_recall(search, project, limit)

        sql = """
            SELECT 
                id, session_id, event_type, content, project, emotion, tags, meta, created_at 
            FROM episodes 
            WHERE 1=1
        """
        params: list[Any] = []

        if project:
            sql += " AND project = ?"
            params.append(project)
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)
        if since:
            sql += " AND created_at >= ?"
            params.append(since)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_episode(row) for row in rows]

    async def _fts_recall(self, search: str, project: str | None, limit: int) -> list[Episode]:
        """High-performance full-text search across episodes."""
        sql = """
            SELECT 
                e.id, e.session_id, e.event_type, e.content, e.project, e.emotion, e.tags, e.meta, e.created_at 
            FROM episodes e
            JOIN episodes_fts f ON e.id = f.rowid
            WHERE f.content MATCH ?
        """
        params: list[Any] = [search]

        if project:
            sql += " AND e.project = ?"
            params.append(project)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_episode(row) for row in rows]

    async def detect_patterns(
        self,
        project: str | None = None,
        min_occurrences: int = 3,
        limit: int = 10,
    ) -> list[Pattern]:
        """
        Sovereign Pattern Analysis.
        Uncovers recurring bottlenecks or successful strategies across sessions.
        """
        sql = "SELECT session_id, event_type, content FROM episodes"
        params: list[Any] = []
        if project:
            sql += " WHERE project = ?"
            params.append(project)

        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return []

        # Computationally expensive operation — ideally offloaded to thread pool under high load
        return _extract_patterns(rows, min_occurrences, limit)

    async def count(self, project: str | None = None) -> int:
        """Sovereign audit: count total temporal memories."""
        sql = "SELECT COUNT(*) FROM episodes"
        params: list[str] = []
        if project:
            sql += " WHERE project = ?"
            params = [project]

        async with self._conn.execute(sql, params) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    def _row_to_episode(self, row: tuple) -> Episode:
        """Map database raw row to Sovereign Episode Model."""
        # Adjust indices based on your actual table schema
        # Order: id, session_id, event_type, content, project, emotion, tags, meta, created_at
        return Episode(
            id=row[0],
            session_id=row[1],
            event_type=row[2],
            content=row[3],
            project=row[4],
            emotion=row[5],
            tags=json.loads(row[6]) if row[6] else [],
            meta=json.loads(row[7]) if row[7] else {},
            created_at=row[8],
        )

    async def get_session_timeline(self, session_id: str) -> list[Episode]:
        """Retrieve chronological history of a specific session."""
        sql = """
            SELECT 
                id, session_id, event_type, content, project, emotion, tags, meta, created_at 
            FROM episodes 
            WHERE session_id = ? 
            ORDER BY created_at ASC
        """
        async with self._conn.execute(sql, (session_id,)) as cursor:
            rows = await cursor.fetchall()
        return [self._row_to_episode(row) for row in rows]


# ─── Pattern Detection (Advanced Algorithmic) ─────────────────────────


def _extract_patterns(
    rows: list[tuple],
    min_occurrences: int,
    limit: int,
) -> list[Pattern]:
    """
    Extract multi-token recurring themes from episode rows.
    Supports Uni-grams and Bi-grams for technical context capture.
    """
    # token -> set of session_ids
    token_sessions: dict[str, set[str]] = defaultdict(set)
    # token -> event types
    token_types: dict[str, list[str]] = defaultdict(list)
    # token -> samples
    token_samples: dict[str, list[str]] = defaultdict(list)

    for session_id, event_type, content in rows:
        # 1. Uni-grams (Smarter filtering)
        tokens = _extract_tokens(content)

        # 2. Bi-grams (Combined significant tokens)
        bigrams = {f"{a} {b}" for a, b in combinations(sorted(tokens), 2)}

        # Merge all candidate themes
        for candidate in tokens | bigrams:
            token_sessions[candidate].add(session_id)
            token_types[candidate].append(event_type)
            if len(token_samples[candidate]) < 5:
                snippet = content[:150].strip() + "..."
                if snippet not in token_samples[candidate]:
                    token_samples[candidate].append(snippet)

    patterns: list[Pattern] = []
    for theme, sessions in token_sessions.items():
        if len(sessions) >= min_occurrences:
            type_counts = Counter(token_types[theme])
            top_types = [t for t, _ in type_counts.most_common(3)]

            patterns.append(
                Pattern(
                    theme=theme,
                    occurrences=len(sessions),
                    sessions=sorted(sessions),
                    event_types=top_types,
                    sample_content=token_samples[theme],
                )
            )

    # Sort by 1. Occurrence frequency 2. Pattern complexity (bi-grams > uni-grams)
    patterns.sort(key=lambda p: (p.occurrences, " " in p.theme), reverse=True)
    return patterns[:limit]


def _extract_tokens(text: str) -> set[str]:
    """Sovereign tokenization: captures technical IDs, snake_case, and kebab-case."""
    raw = _TOKEN_RE.findall(text.lower())
    # Filter by stop words and non-numeric noise
    return {t for t in raw if t not in _STOP_WORDS and not t.isdigit() and len(t) >= 4}
