"""
CORTEX v4.0 — Episodic Memory Engine.

Persistent native memory: stores timestamped episodic events (decisions,
errors, discoveries, flow states) across sessions, detects recurring patterns,
and generates optimized boot payloads for session initialization.

Eliminates the need for manual context-snapshot.md loading.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cortex.temporal import now_iso

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.episodic")

# Valid event types
EVENT_TYPES = frozenset(
    {
        "decision",
        "error",
        "discovery",
        "flow_state",
        "insight",
        "milestone",
        "blocked",
        "resolved",
    }
)

# Valid emotions
EMOTIONS = frozenset(
    {
        "neutral",
        "frustrated",
        "confident",
        "curious",
        "flow",
        "blocked",
        "excited",
        "cautious",
    }
)

# Stop words for pattern detection
_STOP_WORDS = frozenset(
    {
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
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "no",
        "so",
        "if",
        "then",
        "than",
        "that",
        "this",
        "it",
        "its",
        "de",
        "en",
        "la",
        "el",
        "los",
        "las",
        "un",
        "una",
        "del",
        "al",
        "con",
        "por",
        "para",
        "que",
        "se",
        "es",
        "como",
        "más",
        "y",
        "o",
        "su",
        "lo",
    }
)

_TOKEN_RE = re.compile(r"[a-záéíóúñ]{3,}", re.IGNORECASE)


# ─── Data Models ─────────────────────────────────────────────────────


@dataclass
class Episode:
    """A single episodic memory event."""

    id: int
    session_id: str
    event_type: str
    content: str
    project: str | None
    emotion: str
    tags: list[str]
    meta: dict
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "content": self.content,
            "project": self.project,
            "emotion": self.emotion,
            "tags": self.tags,
            "meta": self.meta,
            "created_at": self.created_at,
        }


@dataclass
class Pattern:
    """A recurring theme detected across sessions."""

    theme: str
    occurrences: int
    sessions: list[str]
    event_types: list[str]
    sample_content: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "occurrences": self.occurrences,
            "sessions": self.sessions[:5],
            "event_types": self.event_types,
            "sample_content": self.sample_content[:3],
        }


# ─── Episodic Memory Engine ─────────────────────────────────────────


class EpisodicMemory:
    """Persistent episodic memory for cross-session learning.

    Stores timestamped events, retrieves them by flexible filters,
    and detects recurring patterns using lightweight token analysis.
    """

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def record(
        self,
        session_id: str,
        event_type: str,
        content: str,
        project: str | None = None,
        emotion: str = "neutral",
        tags: list[str] | None = None,
        meta: dict | None = None,
    ) -> int:
        """Store an episodic event.

        Args:
            session_id: Identifier grouping events to a conversation/session.
            event_type: Classification (decision, error, discovery, etc.).
            content: What happened — the episodic memory content.
            project: Associated project name.
            emotion: Emotional state during the event.
            tags: Optional tags for categorization.
            meta: Optional JSON metadata.

        Returns:
            The ID of the stored episode.
        """
        if event_type not in EVENT_TYPES:
            event_type = "insight"  # fallback

        if emotion not in EMOTIONS:
            emotion = "neutral"

        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})

        async with self.conn.execute(
            """
            INSERT INTO episodes (session_id, event_type, content, project,
                                  emotion, tags, meta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, event_type, content, project, emotion, tags_json, meta_json, now_iso()),
        ) as cursor:
            episode_id = cursor.lastrowid

        # Sync FTS
        await self.conn.execute(
            "INSERT INTO episodes_fts(rowid, content, event_type, project) VALUES (?, ?, ?, ?)",
            (episode_id, content, event_type, project or ""),
        )
        await self.conn.commit()

        logger.info(
            "Episode recorded: id=%d type=%s project=%s",
            episode_id,
            event_type,
            project,
        )
        return episode_id

    async def recall(
        self,
        project: str | None = None,
        event_type: str | None = None,
        since: str | None = None,
        limit: int = 20,
        search: str | None = None,
    ) -> list[Episode]:
        """Retrieve episodes with flexible filtering.

        Args:
            project: Filter by project.
            event_type: Filter by event type.
            since: ISO timestamp — only episodes after this time.
            limit: Maximum results.
            search: Full-text search query.

        Returns:
            List of Episode objects, most recent first.
        """
        if search:
            return await self._fts_recall(search, project, limit)

        conditions: list[str] = []
        params: list[str | int] = []

        if project:
            conditions.append("project = ?")
            params.append(project)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if since:
            conditions.append("created_at >= ?")
            params.append(since)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT id, session_id, event_type, content, project,
                   emotion, tags, meta, created_at
            FROM episodes
            {where}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_episode(row) for row in rows]

    async def _fts_recall(
        self,
        search: str,
        project: str | None,
        limit: int,
    ) -> list[Episode]:
        """Full-text search recall."""
        if project:
            query = """
                SELECT e.id, e.session_id, e.event_type, e.content, e.project,
                       e.emotion, e.tags, e.meta, e.created_at
                FROM episodes e
                JOIN episodes_fts fts ON e.id = fts.rowid
                WHERE episodes_fts MATCH ? AND e.project = ?
                ORDER BY rank
                LIMIT ?
            """
            params: list[str | int] = [search, project, limit]
        else:
            query = """
                SELECT e.id, e.session_id, e.event_type, e.content, e.project,
                       e.emotion, e.tags, e.meta, e.created_at
                FROM episodes e
                JOIN episodes_fts fts ON e.id = fts.rowid
                WHERE episodes_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            params = [search, limit]

        try:
            async with self.conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
            return [self._row_to_episode(row) for row in rows]
        except sqlite3.OperationalError:
            logger.debug("FTS query failed, falling back to LIKE", exc_info=True)
            return await self.recall(project=project, limit=limit)

    async def get_session_timeline(self, session_id: str) -> list[Episode]:
        """Retrieve all episodes for a session, ordered chronologically."""
        async with self.conn.execute(
            """
            SELECT id, session_id, event_type, content, project,
                   emotion, tags, meta, created_at
            FROM episodes
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_episode(row) for row in rows]

    async def detect_patterns(
        self,
        project: str | None = None,
        min_occurrences: int = 3,
        limit: int = 10,
    ) -> list[Pattern]:
        """Detect recurring themes across sessions.

        Uses lightweight token frequency analysis on episode content.
        No LLM required — pure algorithmic pattern detection.

        Args:
            project: Scope patterns to a specific project.
            min_occurrences: Minimum sessions where a theme must appear.
            limit: Maximum patterns to return.

        Returns:
            List of Pattern objects, sorted by occurrence count (desc).
        """
        conditions: list[str] = []
        params: list[str | int] = []

        if project:
            conditions.append("project = ?")
            params.append(project)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT session_id, event_type, content
            FROM episodes
            {where}
            ORDER BY created_at DESC
            LIMIT 500
        """

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return []

        return _extract_patterns(rows, min_occurrences, limit)

    async def count(self, project: str | None = None) -> int:
        """Count total episodes, optionally filtered by project."""
        if project:
            async with self.conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE project = ?",
                (project,),
            ) as cursor:
                row = await cursor.fetchone()
        else:
            async with self.conn.execute("SELECT COUNT(*) FROM episodes") as cursor:
                row = await cursor.fetchone()

        return row[0] if row else 0

    @staticmethod
    def _row_to_episode(row: tuple) -> Episode:
        """Convert a DB row tuple to an Episode object."""
        (
            ep_id,
            session_id,
            event_type,
            content,
            project,
            emotion,
            tags_raw,
            meta_raw,
            created_at,
        ) = row

        try:
            tags = json.loads(tags_raw) if tags_raw else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        try:
            meta = json.loads(meta_raw) if meta_raw else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}

        return Episode(
            id=ep_id,
            session_id=session_id,
            event_type=event_type,
            content=content,
            project=project,
            emotion=emotion or "neutral",
            tags=tags,
            meta=meta,
            created_at=created_at,
        )


# ─── Pattern Detection (Pure Algorithmic) ────────────────────────────


def _extract_patterns(
    rows: list[tuple],
    min_occurrences: int,
    limit: int,
) -> list[Pattern]:
    """Extract recurring themes from episode rows using token frequency.

    Groups significant tokens by the sessions they appear in.
    A theme is "recurring" if the same token cluster appears
    in >= min_occurrences distinct sessions.
    """
    # token -> set of session_ids
    token_sessions: dict[str, set[str]] = defaultdict(set)
    # token -> list of event_types
    token_types: dict[str, list[str]] = defaultdict(list)
    # token -> sample content
    token_samples: dict[str, list[str]] = defaultdict(list)

    for session_id, event_type, content in rows:
        tokens = _extract_tokens(content)
        for token in tokens:
            token_sessions[token].add(session_id)
            token_types[token].append(event_type)
            if len(token_samples[token]) < 3:
                snippet = content[:120]
                if snippet not in token_samples[token]:
                    token_samples[token].append(snippet)

    patterns: list[Pattern] = []
    for token, sessions in token_sessions.items():
        if len(sessions) >= min_occurrences:
            type_counts = Counter(token_types[token])
            top_types = [t for t, _ in type_counts.most_common(3)]
            patterns.append(
                Pattern(
                    theme=token,
                    occurrences=len(sessions),
                    sessions=sorted(sessions),
                    event_types=top_types,
                    sample_content=token_samples[token],
                )
            )

    patterns.sort(key=lambda p: p.occurrences, reverse=True)
    return patterns[:limit]


def _extract_tokens(text: str) -> set[str]:
    """Extract significant tokens from text, ignoring stop words."""
    raw = _TOKEN_RE.findall(text.lower())
    return {t for t in raw if t not in _STOP_WORDS and len(t) >= 4}
