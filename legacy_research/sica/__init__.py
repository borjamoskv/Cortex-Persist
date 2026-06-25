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

from legacy_research.sica.agent import SICAAgent
from legacy_research.sica.autonomy import (
    AdaptiveRetry,
    AutonomousTick,
    MetaMetaController,
    SpeculativeFork,
    TraceSynthesizer,
)
from legacy_research.sica.constitution import Constitution, Principle
from legacy_research.sica.meta_level import MetaJudgment, MetaLevel
from legacy_research.sica.object_level import ExecutionTrace, ObjectLevel
from legacy_research.sica.persistence import (
    load_genome,
    load_or_default,
    save_genome,
)
from legacy_research.sica.strategy import (
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
