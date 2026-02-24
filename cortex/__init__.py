"""
CORTEX — The Sovereign Ledger for AI Agents.

Local-first memory infrastructure with vector search, temporal facts,
and cryptographic vaults. Zero network dependencies.
"""

import sys

try:
    # Use pysqlite3 if available (allows newer SQLite versions + extensions)
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

__version__ = "0.3.0b1"
__author__ = "Borja Moskv"

from cortex.engine import CortexEngine

# Experimental modules (optional — not part of core package)
try:
    from .experimental import (  # noqa: F401
        autopoiesis,
        circadian_cycle,
        digital_endocrine,
        epigenetic_memory,
        strategic_disobedience,
        zero_prompting,
    )
except ImportError:
    pass

__all__ = ["CortexEngine", "__version__"]

