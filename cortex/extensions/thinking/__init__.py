"""CORTEX v5.0 — Thought Orchestra Module.

Orquestación multi-modelo con fusión por consenso.
N modelos piensan en paralelo, sus respuestas se fusionan
para producir una respuesta superior a cualquier modelo individual.
"""

from cortex.extensions.thinking.fusion import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThinkingHistory,
    ThoughtFusion,
)
from cortex.extensions.thinking.orchestra import ThoughtOrchestra
from cortex.extensions.thinking.pool import ThinkingRecord
from cortex.extensions.thinking.presets import OrchestraConfig, ThinkingMode

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
