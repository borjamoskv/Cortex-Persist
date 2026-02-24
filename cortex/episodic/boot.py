"""
CORTEX v5.1 — Episodic Boot Engine.

Generates optimized session boot payloads that replace manual
context-snapshot.md loading. Combines:
  1. Recent episodic memories (last 48h)
  2. Detected behavioral patterns
  3. Injected reflections (past learnings)
  4. Context inference (current project)

Output: compact markdown or JSON ready for system_prompt injection.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Final

from cortex.episodic.main import Episode, EpisodicMemory, Pattern
from cortex.memory.temporal import now_iso

__all__ = [
    "BootPayload",
    "DEFAULT_LOOKBACK_HOURS",
    "MAX_BOOT_CHARS",
    "generate_session_boot",
]

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.episodic.boot")

# Boot payload target size (characters)
MAX_BOOT_CHARS: Final[int] = 4000
# Default lookback window for episodes
DEFAULT_LOOKBACK_HOURS: Final[int] = 48

# Event-type → emoji mapping (immutable)
_EVENT_EMOJI: Final[dict[str, str]] = {
    "decision": "⚡",
    "error": "🔴",
    "discovery": "🔍",
    "flow_state": "🌊",
    "insight": "💡",
    "milestone": "🏁",
    "blocked": "🚧",
    "resolved": "✅",
}


# ─── Models ──────────────────────────────────────────────────────────


@dataclass(slots=True)
class BootPayload:
    """Complete session boot payload."""

    timestamp: str
    active_project: str | None
    confidence: str
    episodes: list[Episode]
    patterns: list[Pattern]
    reflections: list[dict]
    summary: str
    total_episodes: int
    semantic_recalls: list[dict] | None = None  # L2 vector results

    def to_dict(self) -> dict:
        result = {
            "timestamp": self.timestamp,
            "active_project": self.active_project,
            "confidence": self.confidence,
            "episodes": [e.to_dict() for e in self.episodes],
            "patterns": [p.to_dict() for p in self.patterns],
            "reflections": self.reflections,
            "summary": self.summary,
            "total_episodes": self.total_episodes,
        }
        if self.semantic_recalls:
            result["semantic_recalls"] = self.semantic_recalls
        return result

    def to_markdown(self) -> str:
        """Render as compact markdown for system_prompt injection."""
        lines = [
            "# 🧠 CORTEX — Session Boot (Episodic Memory)",
            "",
            f"> Generated: {self.timestamp}",
            f"> Active project: **{self.active_project or 'Unknown'}** ({self.confidence})",
            f"> Total episodes in memory: {self.total_episodes}",
            "",
        ]

        _render_episodes(lines, self.episodes)
        _render_patterns(lines, self.patterns)
        _render_reflections(lines, self.reflections)
        _render_semantic_recalls(lines, self.semantic_recalls)

        if self.summary:
            lines += ["## Context", "", self.summary, ""]

        return "\n".join(lines)


# ─── Markdown Section Renderers ──────────────────────────────────────


def _render_episodes(lines: list[str], episodes: list[Episode]) -> None:
    """Append episode entries to the markdown output."""
    if not episodes:
        return
    lines.append("## Recent Memory")
    lines.append("")
    for ep in episodes:
        emoji = _EVENT_EMOJI.get(ep.event_type, "📌")
        lines.append(f"- {emoji} **{ep.event_type}** [{ep.project or '—'}] {ep.content[:150]}")
    lines.append("")


def _render_patterns(lines: list[str], patterns: list[Pattern]) -> None:
    """Append pattern entries to the markdown output."""
    if not patterns:
        return
    lines.append("## Recurring Patterns")
    lines.append("")
    for p in patterns:
        lines.append(
            f"- 🔄 **{p.theme}** — {p.occurrences} sessions ({', '.join(p.event_types[:2])})"
        )
    lines.append("")


def _render_reflections(lines: list[str], reflections: list[dict]) -> None:
    """Append reflection entries to the markdown output."""
    if not reflections:
        return
    lines.append("## Past Learnings")
    lines.append("")
    for r in reflections[:5]:
        content = r.get("content", "")[:120]
        lines.append(f"- 💡 {content}")
    lines.append("")


def _render_semantic_recalls(lines: list[str], recalls: list[dict] | None) -> None:
    """Append L2 semantic recall entries to the markdown output."""
    if not recalls:
        return
    lines.append("## Semantic Memory (L2)")
    lines.append("")
    for sr in recalls[:5]:
        score = sr.get("score", 0)
        content = sr.get("content", "")[:120]
        lines.append(f"- 🧬 [{score:.2f}] {content}")
    lines.append("")


# ─── Boot Generator ─────────────────────────────────────────────────


async def generate_session_boot(
    conn: aiosqlite.Connection,
    project_hint: str | None = None,
    top_k: int = 10,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
) -> BootPayload:
    """Generate a session boot payload.

    This is the primary function that replaces manual context-snapshot.md loading.
    It fuses multiple memory sources into a single, compact payload.

    Args:
        conn: Active aiosqlite connection.
        project_hint: Optional project name to focus on.
        top_k: Number of recent episodes to include.
        lookback_hours: How far back to look for episodes.

    Returns:
        BootPayload with all memory sources combined.
    """
    memory = EpisodicMemory(conn)

    # 1. Compute lookback timestamp
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    since_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    # 2. Recall recent episodes
    episodes = await memory.recall(
        project=project_hint,
        since=since_iso,
        limit=top_k,
    )

    # 3. Detect patterns
    patterns = await memory.detect_patterns(
        project=project_hint,
        min_occurrences=2,
        limit=5,
    )

    # 4. Inject reflections (best-effort)
    reflections = await _get_reflections(conn, project_hint, top_k=5)

    # 5. Context inference (best-effort)
    active_project, confidence, summary = await _get_context_inference(conn, project_hint)

    # 6. Total count
    total = await memory.count(project=project_hint)

    # 7. L2 Semantic Recall (best-effort)
    semantic_recalls = await _get_semantic_recalls(project_hint, top_k=5)

    return BootPayload(
        timestamp=now_iso(),
        active_project=active_project or project_hint,
        confidence=confidence,
        episodes=episodes,
        patterns=patterns,
        reflections=reflections,
        summary=summary,
        total_episodes=total,
        semantic_recalls=semantic_recalls,
    )


# ─── Helper Queries ──────────────────────────────────────────────────


async def _get_reflections(
    conn: aiosqlite.Connection,
    project: str | None,
    top_k: int = 5,
) -> list[dict]:
    """Retrieve recent reflections from facts table (best-effort)."""
    try:
        conditions = ["fact_type IN ('reflection', 'error', 'meta_learning')"]
        params: list[object] = []

        if project:
            conditions.append("project = ?")
            params.append(project)

        conditions.append("valid_until IS NULL")

        where = " AND ".join(conditions)
        query = f"""
            SELECT id, project, content, fact_type, created_at
            FROM facts
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(top_k)

        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "project": row[1],
                "content": row[2],
                "type": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.debug("Failed to retrieve reflections: %s", e, exc_info=True)
        return []


async def _get_context_inference(
    conn: aiosqlite.Connection,
    project_hint: str | None,
) -> tuple[str | None, str, str]:
    """Get latest context inference snapshot (best-effort).

    Returns:
        Tuple of (active_project, confidence, summary).
    """
    try:
        async with conn.execute(
            """
            SELECT active_project, confidence, summary
            FROM context_snapshots
            ORDER BY id DESC
            LIMIT 1
            """,
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            return row[0], row[1], row[2]
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.debug("Failed to retrieve context inference: %s", e, exc_info=True)

    return project_hint, "C1", "No context inference available."


async def _get_semantic_recalls(
    project_hint: str | None,
    top_k: int = 5,
) -> list[dict] | None:
    """Retrieve semantically relevant L2 memories (best-effort).

    Returns None if the vector store is not configured or unavailable.
    Never raises — all failures degrade gracefully to None.
    """
    try:
        from cortex.config import VECTOR_STORE_PATH
        from cortex.memory import AsyncEncoder, VectorStoreL2

        if not VECTOR_STORE_PATH:
            return None

        encoder = AsyncEncoder()
        store = VectorStoreL2(encoder=encoder, db_path=VECTOR_STORE_PATH)

        query = project_hint or "recent work"
        results = await store.recall(query=query, limit=top_k, project=project_hint)
        await store.close()

        return results if results else None
    except (ImportError, sqlite3.Error, OSError, RuntimeError, ValueError) as e:
        logger.debug("L2 semantic recall unavailable: %s", e)
        return None
