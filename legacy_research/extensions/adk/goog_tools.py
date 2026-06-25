# [C5-REAL] Exergy-Maximized
"""Google One Tools - Integration for CORTEX ADK agents.

Re-exports from legacy_research.adk.goog_tools to avoid code duplication.
"""

from legacy_research.adk.goog_tools import (
    GOOGLE_ONE_TOOLS,
    goog_backup_cortex,
    goog_quota,
    goog_sync_notebooklm,
)

__all__ = [
    "GOOGLE_ONE_TOOLS",
    "goog_backup_cortex",
    "goog_quota",
    "goog_sync_notebooklm",
]
