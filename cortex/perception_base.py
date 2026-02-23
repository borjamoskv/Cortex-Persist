"""
CORTEX v5.1 — Perception Base & Models.

Foundational types and classification logic used by the Perception Engine.
Optimized for high-frequency file event processing and project inference.
Provides the data schema for user behavioral state tracking (Industrial Noir).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# ─── Constants ───────────────────────────────────────────────────────

DEBOUNCE_SECONDS: Final[float] = 2.0
INFERENCE_WINDOW_SECONDS: Final[int] = 300  # 5 minutes
RECORD_COOLDOWN_SECONDS: Final[int] = 300  # 1 episode per 5min per project
MIN_EVENTS_FOR_INFERENCE: Final[int] = 3  # need at least 3 events to infer

# Pre-compiled extension mapping for O(1) classification of common files
_EXT_ROLES: Final[dict[str, str]] = {
    # Source
    ".py": "source",
    ".ts": "source",
    ".tsx": "source",
    ".js": "source",
    ".jsx": "source",
    ".swift": "source",
    ".rs": "source",
    ".go": "source",
    ".css": "source",
    ".html": "source",
    ".c": "source",
    ".cpp": "source",
    # Config
    ".json": "config",
    ".toml": "config",
    ".yaml": "config",
    ".yml": "config",
    ".ini": "config",
    ".env": "config",
    "Makefile": "config",
    "Dockerfile": "config",
    # Docs
    ".md": "docs",
    ".txt": "docs",
    ".rst": "docs",
    ".pdf": "docs",
    # Assets
    ".png": "asset",
    ".jpg": "asset",
    ".jpeg": "asset",
    ".svg": "asset",
    ".webp": "asset",
    ".gif": "asset",
    ".ico": "asset",
    ".mp3": "asset",
    ".mp4": "asset",
    ".woff": "asset",
    ".woff2": "asset",
    ".ttf": "asset",
}

# Regex fallbacks for more complex patterns (e.g. test files)
_ROLE_PATTERNS: Final[list[tuple[str, re.Pattern]]] = [
    ("test", re.compile(r"(test_|_test\.|spec\.|\.test\.)", re.IGNORECASE)),
]

# Git/hidden paths to always ignore (Comprehensive list)
_IGNORE_PATTERNS: Final[re.Pattern] = re.compile(
    r"(\.git/|__pycache__/|\.pyc$|node_modules/|\.DS_Store|\.venv/|\.pytest_cache/|dist/|build/|\.next/|\.turbo/)"
)


@dataclass(slots=True)
class FileEvent:
    """A single file system event after debouncing."""

    path: str
    event_type: str  # created, modified, deleted, moved
    role: str  # test, config, docs, asset, source, unknown
    project: str | None
    timestamp: float

    @property
    def basename(self) -> str:
        """Name of the file without directory path."""
        return Path(self.path).name


@dataclass(slots=True)
class BehavioralSnapshot:
    """Inferred user behavior from a window of file events."""

    intent: str  # debugging, deep_work, refactoring, setup, etc.
    emotion: str  # frustrated, flow, curious, cautious, confident, neutral
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
            "top_files": self.top_files[:10],  # Increased visibility
            "summary": self.summary,
            "timestamp": self.timestamp,
        }


# ─── Classification Logic ────────────────────────────────────────────


def classify_file(path: str) -> str:
    """
    Classify a file path into a role category.
    Uses O(1) extension mapping first, then regex for complex roles like tests.
    """
    p = Path(path)

    # 1. Check complex patterns first (Test files often have source extensions)
    for role, pattern in _ROLE_PATTERNS:
        if pattern.search(path):
            return role

    # 2. Check O(1) extension lookup
    ext = p.suffix.lower()
    if ext in _EXT_ROLES:
        return _EXT_ROLES[ext]

    # 3. Check exact filenames (Makefile, Dockerfile)
    if p.name in _EXT_ROLES:
        return _EXT_ROLES[p.name]

    return "unknown"


def infer_project_from_path(path: str, workspace_root: str | None = None) -> str | None:
    """
    Infer project name from file path with support for monorepo structures.
    Recognizes 'packages/', 'apps/', and 'services/' sub-layouts.
    """
    p = Path(path)

    if workspace_root:
        root = Path(workspace_root)
        try:
            rel = p.relative_to(root)
            parts = rel.parts
            if not parts:
                return root.name

            # Monorepo detection: packages/my-pkg -> my-pkg
            if len(parts) >= 2 and parts[0] in ("packages", "apps", "services", "src"):
                return parts[1]

            return parts[0]
        except ValueError:
            pass

    # Fallback: scan up parents until we find a common project marker or root
    for parent in p.parents:
        if parent.name in (".", "/"):
            break
        # Ignore intermediate common dirs
        if parent.name not in ("src", "lib", "internal", "pkg", "docs", "tests"):
            return parent.name

    return None


def should_ignore(path: str) -> bool:
    """Check if a path should be ignored (git, node_modules, build artifacts)."""
    return bool(_IGNORE_PATTERNS.search(path))
