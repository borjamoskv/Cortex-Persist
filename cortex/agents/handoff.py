# [C5-REAL] Exergy-Maximized
"""Session Handoff Protocol.

Wrapper redirecting to cortex.extensions.agents.handoff to eliminate code duplication.
"""

from __future__ import annotations

from cortex.extensions.agents.handoff import (
    DEFAULT_HANDOFF_PATH,
    HANDOFF_VERSION,
    MAX_DECISIONS,
    MAX_ERRORS,
    MAX_GHOSTS,
    generate_handoff,
    load_handoff,
    save_handoff,
)

__all__ = [
    "DEFAULT_HANDOFF_PATH",
    "HANDOFF_VERSION",
    "MAX_DECISIONS",
    "MAX_ERRORS",
    "MAX_GHOSTS",
    "generate_handoff",
    "load_handoff",
    "save_handoff",
]
