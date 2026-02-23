"""
CORTEX v5.0 — Perception Base & Models.

Foundational types and classification logic used by the Perception Engine.
Extracted to improve architectural modularity and reduce cognition-fatigue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# ─── Constants ───────────────────────────────────────────────────────

DEBOUNCE_SECONDS: Final[float] = 2.0
INFERENCE_WINDOW_SECONDS: Final[int] = 300  # 5 minutes
RECORD_COOLDOWN_SECONDS: Final[int] = 300   # 1 episode per 5min per project
MIN_EVENTS_FOR_INFERENCE: Final[int] = 3    # need at least 3 events to infer

# File classification patterns
_FILE_ROLES: Final[list[tuple[str, re.Pattern]]] = [
    ("test", re.compile(r"(test_|_test\.|spec\.|\.test\.)", re.IGNORECASE)),
    (
        "config",
        re.compile(
            r"(\.env|config\.|settings\.|\.toml|\.ini|\.ya?ml|Makefile|Dockerfile|\.json$)",
            re.IGNORECASE,
        ),
    ),
    ("docs", re.compile(r"(\.md$|\.rst$|\.txt$|README|CHANGELOG|docs/)", re.IGNORECASE)),
    ("asset", re.compile(r"\.(png|jpg|svg|ico|woff|ttf|mp3|mp4|webp)$", re.IGNORECASE)),
    ("source", re.compile(r"\.(py|ts|tsx|js|jsx|swift|rs|go|css|html)$", re.IGNORECASE)),
]

# Git/hidden paths to always ignore
_IGNORE_PATTERNS: Final[re.Pattern] = re.compile(
    r"(\.git/|__pycache__|\.pyc$|node_modules/|\.DS_Store|\.venv/|\.pytest_cache)"
)


@dataclass(slots=True)
class FileEvent:
    """A single file system event after debouncing."""
    path: str
    event_type: str  # created, modified, deleted, moved
    role: str       # test, config, docs, asset, source, unknown
    project: str | None
    timestamp: float

    @property
    def basename(self) -> str:
        """Name of the file without directory path."""
        return Path(self.path).name


@dataclass(slots=True)
class BehavioralSnapshot:
    """Inferred user behavior from a window of file events."""
    intent: str      # debugging, deep_work, refactoring, setup, etc.
    emotion: str     # frustrated, flow, curious, cautious, confident, neutral
    confidence: str  # C1-C5
    project: str | None
    event_count: int
    window_seconds: float
    top_files: list[str]
    summary: str
    timestamp: str

    def to_dict(self) -> dict:
        """JSON-serializable representation."""
        return {
            "intent": self.intent,
            "emotion": self.emotion,
            "confidence": self.confidence,
            "project": self.project,
            "event_count": self.event_count,
            "window_seconds": round(self.window_seconds, 1),
            "top_files": self.top_files[:5],
            "summary": self.summary,
            "timestamp": self.timestamp,
        }


# ─── Classification Logic ────────────────────────────────────────────


def classify_file(path: str) -> str:
    """Classify a file path into a role category."""
    for role, pattern in _FILE_ROLES:
        if pattern.search(path):
            return role
    return "unknown"


def infer_project_from_path(path: str, workspace_root: str | None = None) -> str | None:
    """Infer project name from file path."""
    p = Path(path)

    if workspace_root:
        root = Path(workspace_root)
        try:
            rel = p.relative_to(root)
            parts = rel.parts
            if parts:
                return parts[0] if len(parts) > 1 else root.name
        except ValueError:
            pass

    # Fallback: use parent directory name
    if p.parent.name and p.parent.name not in (".", "/"):
        return p.parent.name

    return None


def should_ignore(path: str) -> bool:
    """Check if a path should be ignored."""
    return bool(_IGNORE_PATTERNS.search(path))
