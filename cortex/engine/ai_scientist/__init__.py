"""
CORTEX-Persist AI Scientist Orchestrator.

[C5-REAL] Exergy-Maximized Pipeline.
Fully autonomous research generation loop:
Idea -> Code -> Execute -> Analyze -> Write -> Review.
"""

from .analyst_writer import AnalystWriter
from .coder_executor import CoderExecutor
from .idea_generator import IdeaGenerator
from .orchestrator import AIScientistOrchestrator
from .reviewer import AdversarialReviewer

__all__ = [
    "AIScientistOrchestrator",
    "IdeaGenerator",
    "CoderExecutor",
    "AnalystWriter",
    "AdversarialReviewer",
]
