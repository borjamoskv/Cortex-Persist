"""
CORTEX Git Poet — Re-export Shim
==================================
Original location of the CommitPoet class, now consolidated into
``cortex.engine.poet``. This module re-exports all public symbols
for backward compatibility.
"""

from __future__ import annotations

# Re-export from canonical engine location
from cortex.engine.poet import (
    CommitPoet,
    generate_candidates,
    generate_commit_message,
)

__all__ = ["CommitPoet", "generate_candidates", "generate_commit_message"]
