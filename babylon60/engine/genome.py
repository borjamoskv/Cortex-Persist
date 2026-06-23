# [C5-REAL] Exergy-Maximized
"""Strategy Genome - Code-as-Data Foundation for L7 Autopoiesis.

A StrategyGenome is a serializable dict that encodes:
1. An ISA dispatch tree (the "phenotype" - what the agent DOES)
2. Strategy parameters (the "genotype" - HOW it does it)
3. Mutation operators (the "mutagen" - HOW it changes itself)
4. Fitness history (the "lineage" - HOW WELL it performed)

This is Python's answer to Lisp's code-as-data:
- quote  → to_dict() / to_json()  (freeze code into data)
- transform → mutate() / crossover()  (manipulate frozen code)
- eval  → compile() / execute()  (thaw data back into code)

The genome is the unit of evolution. Everything the agent IS
can be serialized, mutated, measured, and selected.

Reality Level: C5-REAL
"""

from __future__ import annotations

from babylon60.engine._genome_mutator import GenomeMutator
from babylon60.engine._genome_types import (
    FitnessRecord,
    Lineage,
    MutationType,
    StrategyGenome,
)

__all__ = [
    "FitnessRecord",
    "GenomeMutator",
    "Lineage",
    "MutationType",
    "StrategyGenome",
]
