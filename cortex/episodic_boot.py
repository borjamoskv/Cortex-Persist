"""
CORTEX v4.0 — Episodic Boot Engine.

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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from cortex.episodic import Episode, EpisodicMemory, Pattern
from cortex.temporal import now_iso

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.episodic.boot")

# Boot payload target size (characters)
MAX_BOOT_CHARS = 4000
# Default lookback window for episodes
DEFAULT_LOOKBACK_HOURS = 48


@dataclass
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

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "active_project": self.active_project,
            "confidence": self.confidence,
            "episodes": [e.to_dict() for e in self.episodes],
            "patterns": [p.to_dict() for p in self.patterns],
            "reflections": self.reflections,
            "summary": self.summary,
            "total_episodes": self.total_episodes,
        }

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

        # Recent episodes
        if self.episodes:
            lines.append("## Recent Memory")
            lines.append("")
            for ep in self.episodes:
                emoji = _event_emoji(ep.event_type)
                lines.append(
                    f"- {emoji} **{ep.event_type}** [{ep.project or '—'}] {ep.content[:150]}"
                )
            lines.append("")

        # Patterns
        if self.patterns:
            lines.append("## Recurring Patterns")
            lines.append("")
            for p in self.patterns:
                lines.append(
                    f"- 🔄 **{p.theme}** — {p.occurrences} sessions "
                    f"({', '.join(p.event_types[:2])})"
                )
            lines.append("")

        # Reflections
        if self.reflections:
            lines.append("## Past Learnings")
            lines.append("")
            for r in self.reflections[:5]:
                content = r.get("content", "")[:120]
                lines.append(f"- 💡 {content}")
            lines.append("")

        # Summary
        if self.summary:
            lines.append("## Context")
            lines.append("")
            lines.append(self.summary)
            lines.append("")

        return "\n".join(lines)


def _event_emoji(event_type: str) -> str:
    """Map event type to emoji."""
    return {
        "decision": "⚡",
        "error": "🔴",
        "discovery": "🔍",
        "flow_state": "🌊",
        "insight": "💡",
        "milestone": "🏁",
        "blocked": "🚧",
        "resolved": "✅",
    }.get(event_type, "📌")


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

    return BootPayload(
        timestamp=now_iso(),
        active_project=active_project or project_hint,
        confidence=confidence,
        episodes=episodes,
        patterns=patterns,
        reflections=reflections,
        summary=summary,
        total_episodes=total,
    )


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
    except Exception as e:
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
    except Exception as e:
        logger.debug("Failed to retrieve context inference: %s", e, exc_info=True)

    return project_hint, "C1", "No context inference available."
