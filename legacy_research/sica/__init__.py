# [C5-REAL] Exergy-Maximized
"""SICA - Self-Improving Cognitive Architecture.

Nelson-Narens (1990) dual-level metacognitive agent framework.

The META-LEVEL monitors and controls the OBJECT-LEVEL:
  - MONITOR (bottom-up): observes execution traces, error patterns, strategy fitness
  - CONTROL (top-down): mutates search strategies, adjusts tool selection, rewrites heuristics

Distinguishes between:
  - "I failed at the task" → object-level correction
  - "I failed at HOW I THINK about the task" → meta-level strategy mutation

Constitutional evaluation layer inspired by Anthropic Constitutional AI:
  each output is judged against immutable retrieval principles before emission.
"""

from __future__ import annotations

from cortex.sica.agent import SICAAgent
from cortex.sica.autonomy import (
    AdaptiveRetry,
    AutonomousTick,
    MetaMetaController,
    SpeculativeFork,
    TraceSynthesizer,
)
from cortex.sica.constitution import Constitution, Principle
from cortex.sica.meta_level import MetaJudgment, MetaLevel
from cortex.sica.object_level import ExecutionTrace, ObjectLevel
from cortex.sica.persistence import (
    load_genome,
    load_or_default,
    save_genome,
)
from cortex.sica.strategy import (
    SearchStrategy,
    StrategyGenome,
    StrategyMutation,
)

__all__ = [
    "SICAAgent",
    # Autonomy
    "AdaptiveRetry",
    "AutonomousTick",
    "MetaMetaController",
    "SpeculativeFork",
    "TraceSynthesizer",
    # Constitution
    "Constitution",
    "Principle",
    # Meta-level
    "MetaLevel",
    "MetaJudgment",
    # Object-level
    "ObjectLevel",
    "ExecutionTrace",
    # Persistence
    "load_genome",
    "load_or_default",
    "save_genome",
    # Strategy
    "SearchStrategy",
    "StrategyMutation",
    "StrategyGenome",
]
