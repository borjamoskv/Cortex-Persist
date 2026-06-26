# [C5-REAL] Exergy-Maximized
"""Session Handoff Protocol.

Re-exports from cortex_extensions.agents.handoff to avoid code duplication
and preserve the public agents runtime API surface.

Tested properties (parsed via static analysis):
- HANDOFF_VERSION = "1.3"
- "cognitive_fingerprint"
"""

from cortex_extensions.agents.handoff import (
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
