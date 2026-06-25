# [C5-REAL] Exergy-Maximized
"""Thought Orchestra Module.

Orquestación multi-modelo con fusión por consenso.
N modelos piensan en paralelo, sus respuestas se fusionan
para producir una respuesta superior a cualquier modelo individual.
"""

from legacy_research.extensions.thinking.fusion import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThinkingHistory,
    ThoughtFusion,
)
from legacy_research.extensions.thinking.orchestra import ThoughtOrchestra
from legacy_research.extensions.thinking.pool import ThinkingRecord
from legacy_research.extensions.thinking.presets import OrchestraConfig, ThinkingMode

__all__ = [
    "FusedThought",
    "FusionStrategy",
    "ModelResponse",
    "OrchestraConfig",
    "ThinkingHistory",
    "ThinkingMode",
    "ThinkingRecord",
    "ThoughtFusion",
    "ThoughtOrchestra",
]
