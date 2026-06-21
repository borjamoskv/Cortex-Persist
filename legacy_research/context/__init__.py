# [C5-REAL] Exergy-Maximized
"""CORTEX Context - Unified Retrieval Layer.

Assembles context from all knowledge sources (VSA, Facts, KI, SQLite-Vec)
into a single ContextPacket for downstream pipeline consumption.
"""

from cortex.context.assembler import ContextAssembler

__all__ = ["ContextAssembler"]
