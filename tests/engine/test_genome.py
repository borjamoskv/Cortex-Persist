# [C5-REAL] Exergy-Maximized
import pytest
from cortex.engine.genome import StrategyGenome, GenomeMutator, MutationType
from cortex.isa.builder import dispatch, noop, cond, Predicate

def test_genome_creation():
    genome = StrategyGenome(
        name="test_g",
        dispatch_tree=dispatch("target_a", {}),
        parameters={"p1": 42}
    )
    assert genome.name == "test_g"
    assert genome.complexity == 1
    assert "target_a" in genome.targets
    assert genome.parameters["p1"] == 42

def test_causal_patch_mutation():
    # Setup a genome with a dispatch tree containing "failing_target"
    genome = StrategyGenome(
        name="test_causal",
        dispatch_tree=dispatch("failing_target", {}),
        parameters={}
    )
    
    mutator = GenomeMutator()
    # Provide a failure trace specifying the failed_target
    failure_trace = {"failed_target": "failing_target"}
    
    # Run mutate with force_type=MutationType.CAUSAL_PATCH
    child = mutator.mutate(genome, force_type=MutationType.CAUSAL_PATCH, failure_trace=failure_trace)
    
    # Check that it mutated and updated the dispatch tree correctly
    assert child.lineage.generation == 1
    # Check that "failing_target" was replaced by a Cond node containing retry and fallback
    tree = child.dispatch_tree
    assert "Cond" in tree
    cond_data = tree["Cond"]
    assert "then_branch" in cond_data
    assert "else_branch" in cond_data
    
    # The then_branch should be a Dispatch to retry_failing_target
    then_node = cond_data["then_branch"]
    assert then_node["Dispatch"]["target"] == "retry_failing_target"
    
    # The else_branch should be a Dispatch to fallback_failing_target
    else_node = cond_data["else_branch"]
    assert else_node["Dispatch"]["target"] == "fallback_failing_target"

def test_causal_patch_mutation_probability():
    genome = StrategyGenome(
        name="test_causal_prob",
        dispatch_tree=dispatch("failing_target", {}),
        parameters={},
        mutation_rates={MutationType.CAUSAL_PATCH: 1.0}  # Force 100% rate in weights
    )
    
    mutator = GenomeMutator()
    failure_trace = {"failed_target": "failing_target"}
    
    # Since random.random() < 1.0 is always True (or rate is 1.0), this should select CAUSAL_PATCH
    child = mutator.mutate(genome, failure_trace=failure_trace)
    assert "Cond" in child.dispatch_tree
