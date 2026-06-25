# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - B2B Sales Automation Extension.

Exports the Deep Research Agent and context compression utilities
for B2B automated messaging flows.
"""

from legacy_research.extensions.sales_b2b.context_compressor import ContextCompressor
from legacy_research.extensions.sales_b2b.deep_research_agent import B2BDeepResearchAgent
from legacy_research.extensions.sales_b2b.messaging_flow import MessagingFSM, MessagingStage

__all__ = [
    "B2BDeepResearchAgent",
    "ContextCompressor",
    "MessagingFSM",
    "MessagingStage",
]
