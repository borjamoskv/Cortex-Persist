# [C5-REAL] Exergy-Maximized
import pytest
from cortex.sica.strategy import default_genome, Heuristic
from cortex.sica.colony.genetics import GenomeMutator


def test_genome_mutator_spontaneous_injection():
    """Verify GenomeMutator introduces novel variance."""
    genome = default_genome()
    initial_heuristics = len(genome.heuristics)

    mutator = GenomeMutator()
    # Force high mutation rate to ensure an injection or drift happens
    mutated = mutator.mutate(genome, mutation_rate=0.99)

    # We should see a generation bump
    assert mutated.generation == genome.generation + 1
    assert "mut(" in mutated.parent_hash

    # Verify we didn't corrupt the instance
    assert isinstance(mutated.heuristics[0], Heuristic)


def test_genome_mutator_pruning():
    """Verify GenomeMutator prunes poorly performing heuristics."""
    genome = default_genome()
    # Force a very weak heuristic, and pad to exceed the > 3 threshold
    genome.heuristics = [
        Heuristic("dummy1", "pad", weight=0.9),
        Heuristic("dummy2", "pad", weight=0.9),
        Heuristic("dummy3", "pad", weight=0.9),
        Heuristic("weak_link", "to be pruned", weight=0.01),
    ]

    mutator = GenomeMutator()
    mutated = mutator.mutate(genome, mutation_rate=1.0)

    # Pruned?
    assert not any(h.name == "weak_link" for h in mutated.heuristics)
