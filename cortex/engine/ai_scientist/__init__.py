"""
CORTEX-Persist AI Scientist Orchestrator.

[C5-REAL] Exergy-Maximized Pipeline.
Fully autonomous research generation loop:
Idea -> Code -> Execute -> Analyze -> Write -> Review.
"""

from .orchestrator import AIScientistOrchestrator
from .idea_generator import IdeaGenerator
from .coder_executor import CoderExecutor
from .analyst_writer import AnalystWriter
from .reviewer import AdversarialReviewer

__all__ = [
    "AIScientistOrchestrator",
    "IdeaGenerator",
    "CoderExecutor",
    "AnalystWriter",
    "AdversarialReviewer",
]
