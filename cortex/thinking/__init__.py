"""CORTEX v4.3 — Thought Orchestra Module.

Orquestación multi-modelo con fusión por consenso.
N modelos piensan en paralelo, sus respuestas se fusionan
para producir una respuesta superior a cualquier modelo individual.
"""

from cortex.thinking.fusion import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThinkingHistory,
    ThoughtFusion,
)
from cortex.thinking.orchestra import ThoughtOrchestra
from cortex.thinking.pool import ThinkingRecord
from cortex.thinking.presets import OrchestraConfig, ThinkingMode

__all__ = [
    "ThoughtOrchestra",
    "OrchestraConfig",
    "ThinkingMode",
    "ThinkingRecord",
    "ThoughtFusion",
    "FusionStrategy",
    "FusedThought",
    "ModelResponse",
    "ThinkingHistory",
]
