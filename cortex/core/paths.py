# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""CORTEX — Canonical Path Resolution.

Single source of truth for ALL filesystem paths in the codebase.
Every path is overridable via environment variables for portability,
CI, Docker, and third-party onboarding.

Usage::

    from cortex.core.paths import CORTEX_DIR, AGENT_DIR, CORTEX_DB

Environment variables::

    CORTEX_DIR          → ~/.cortex (default)
    CORTEX_AGENT_DIR    → ~/.agent (default)
    CORTEX_DB_NAME      → cortex.db (default, relative to CORTEX_DIR)
    CORTEX_SKILLS_DIR   → ~/.gemini/antigravity/skills (default)
    CORTEX_MODELS_DIR   → ~/.cortex/models (default)
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "AGENT_DIR",
    "COLD_STORAGE_DB",
    "CORTEX_DB",
    "CORTEX_DIR",
    "DAEMON_CONFIG_FILE",
    "DAEMON_STATUS_FILE",
    "MEMORY_DIR",
    "MODELS_DIR",
    "PERSONAL_DB",
    "SKILLS_DIR",
    "SYNC_STATE_FILE",
]

# ─── Core Directories ───────────────────────────────────────────────

CORTEX_DIR: Path = Path(os.environ.get("CORTEX_DIR", Path.home() / ".cortex"))
"""Root CORTEX data directory. Override: CORTEX_DIR env var."""

AGENT_DIR: Path = Path(os.environ.get("CORTEX_AGENT_DIR", Path.home() / ".agent"))
"""Agent configuration and memory directory. Override: CORTEX_AGENT_DIR env var."""

# ─── Database ────────────────────────────────────────────────────────

CORTEX_DB: Path = CORTEX_DIR / os.environ.get("CORTEX_DB_NAME", "cortex.db")
"""Path to the main CORTEX SQLite database."""

PERSONAL_DB: Path = CORTEX_DIR / "personal_memories.db"
"""Repatriated personal/side-project memories (NAROA, LIVENOTCH, etc.)."""

COLD_STORAGE_DB: Path = CORTEX_DIR / "cold_storage.db"
"""Archived test/junk projects. Read-only cold storage."""

# ─── Derived Paths ───────────────────────────────────────────────────

MEMORY_DIR: Path = AGENT_DIR / "memory"
"""Agent memory file directory (ghosts, system, daemon status)."""

DAEMON_CONFIG_FILE: Path = CORTEX_DIR / "daemon_config.json"
"""Daemon configuration file."""

DAEMON_STATUS_FILE: Path = MEMORY_DIR / "daemon_status.json"
"""Daemon status output file."""

SYNC_STATE_FILE: Path = CORTEX_DIR / "sync_state.json"
"""Sync engine state tracking file."""

MODELS_DIR: Path = Path(os.environ.get("CORTEX_MODELS_DIR", str(CORTEX_DIR / "models")))
"""Embedding model cache directory. Override: CORTEX_MODELS_DIR env var."""

SKILLS_DIR: Path = Path(
    os.environ.get(
        "CORTEX_SKILLS_DIR",
        str(Path.home() / ".gemini" / "antigravity" / "skills"),
    )
)
"""Skills base directory. Override: CORTEX_SKILLS_DIR env var."""

# ─── Convenience ─────────────────────────────────────────────────────

AUDIT_LOG_PATH: Path = CORTEX_DIR / "audit.log"
"""Append-only audit log for admin/CLI operations."""

DRIFT_DIR: Path = CORTEX_DIR / "drift"
"""Topological drift signature storage."""
