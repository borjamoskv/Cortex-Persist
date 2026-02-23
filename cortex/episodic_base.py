"""
CORTEX v5.0 — Episodic Base & Models.

Foundational types and constants for the Episodic Memory system.
Extracted to mitigate LOC bloat and enhance maintainability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Any

# ─── Constants ───────────────────────────────────────────────────────

# Episodic event categories
EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "decision",     # Architectural choice, dependency addition, etc.
        "error",        # Resolved traceback or blocker.
        "discovery",    # Integration learned, API quirk found.
        "insight",      # General realization or meta-comment.
        "milestone",    # Feature completion or ship event.
        "flow_state",   # Period of high-density productive activity.
        "blocked",      # Stuck on a bug or missing information.
    }
)

# Valid human/agent emotional states
EMOTIONS: Final[frozenset[str]] = frozenset(
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


@dataclass(slots=True)
class Episode:
    """A single episodic memory event."""
    id: int
    session_id: str
    event_type: str
    content: str
    project: str | None
    emotion: str
    tags: list[str]
    meta: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable representation."""
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


@dataclass(slots=True)
class Pattern:
    """A recurring theme detected across sessions."""
    theme: str
    occurrences: int
    sessions: list[str]
    event_types: list[str]
    sample_content: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable representation."""
        return {
            "theme": self.theme,
            "occurrences": self.occurrences,
            "sessions": self.sessions[:5],
            "event_types": self.event_types,
            "sample_content": self.sample_content[:3],
        }
