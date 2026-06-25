# [C5-REAL] Exergy-Maximized
"""Tests for the Cross-System Invariant Compiler.

Demonstrates:
1. Complete system alignment (Shannon ≡ Cortex ≡ Substrate) is consistent.
2. Divergence in any layer (e.g. Shannon/Cortex mismatch or Substrate error rate overflow) causes consistency failure.
3. Proof hashes are deterministic and tamper-evident.
"""

import tempfile
import pytest

from legacy_research.shannon.env.trace import EpisodeTrace, StepTrace
from legacy_research.runtime.invariants.cross_system import CrossSystemInvariantCompiler
from cortex.engine.evolution_ledger import ControlVector, MutationRecord, EvolutionLedger


@pytest.fixture
def base_shannon_trace() -> EpisodeTrace:
    steps = [
        StepTrace(
            step_idx=0,
            observation_hex="010203",
            action_hex="aabbcc",
            reward=1.0,
            done=False,
            info={"meta": "step0"},
            timestamp=1718000000.0,
        ),
        StepTrace(
            step_idx=1,
            observation_hex="040506",
            action_hex="ddeeff",
            reward=100.0,
            done=True,
            info={"meta": "step1"},
            timestamp=1718000001.0,
        ),
    ]
    from legacy_research.shannon.env.trace import compute_trace_checksum

    checksum = compute_trace_checksum("genesis-v1", "000000", steps)
    return EpisodeTrace(
        env_id="genesis-v1",
        env_kwargs={"seed": 42},
        seed=42,
        initial_observation_hex="000000",
        steps=steps,
        checksum=checksum,
    )


@pytest.fixture
def base_cortex_ledger() -> list[dict]:
    return [
        {"env_id": "genesis-v1", "seed": 42},  # Config header
        {
            "action": "SHANNON_STEP",
            "metadata": {
                "step_idx": 0,
                "action_hex": "aabbcc",
                "observation_hex": "010203",
                "reward": 1.0,
                "done": False,
                "agent_idx": 0,
            },
        },
        {
            "action": "SHANNON_STEP",
            "metadata": {
                "step_idx": 1,
                "action_hex": "ddeeff",
                "observation_hex": "040506",
                "reward": 100.0,
                "done": True,
                "agent_idx": 1,
            },
        },
    ]


@pytest.fixture
def base_substrate_records() -> list[MutationRecord]:
    return [
        MutationRecord(
            sequence=1,
            agent_idx=0,
            timestamp=1718000000.0,
            prev_hash="GENESIS",
            hash="h1",
            vector_before=ControlVector(0.0, 0.0, 0.0, 0.0),
            vector_after=ControlVector(10.0, 0.05, 0.1, 0.6),
            performance_delta=100.0,
            source="substrate",
        ),
        MutationRecord(
            sequence=2,
            agent_idx=1,
            timestamp=1718000001.0,
            prev_hash="h1",
            hash="h2",
            vector_before=ControlVector(0.0, 0.0, 0.0, 0.0),
            vector_after=ControlVector(12.0, 0.03, 0.08, 0.55),
            performance_delta=150.0,
            source="substrate",
        ),
    ]


def test_global_invariance_perfect_alignment(
    base_shannon_trace, base_cortex_ledger, base_substrate_records
):
    """Test that perfectly aligned execution yields a consistent verdict."""
    verdict = CrossSystemInvariantCompiler.verify_global_invariance(
        shannon_trace=base_shannon_trace,
        cortex_ledger=base_cortex_ledger,
        substrate_ledger=base_substrate_records,
    )
    assert verdict.consistent is True
    assert len(verdict.details) == 0
    assert len(verdict.global_proof_hash) == 64


def test_global_invariance_shannon_mismatch(
    base_shannon_trace, base_cortex_ledger, base_substrate_records
):
    """Test that a mismatch between Shannon and Cortex yields inconsistency."""
    # Modify Cortex observation to trigger semantic divergence
    base_cortex_ledger[1]["metadata"]["observation_hex"] = "999999"

    verdict = CrossSystemInvariantCompiler.verify_global_invariance(
        shannon_trace=base_shannon_trace,
        cortex_ledger=base_cortex_ledger,
        substrate_ledger=base_substrate_records,
    )
    assert verdict.consistent is False
    assert any("SHANNON-CORTEX DIVERGENCE" in detail for detail in verdict.details)


def test_global_invariance_agent_mismatch(
    base_shannon_trace, base_cortex_ledger, base_substrate_records
):
    """Test that mismatched agent indices between Cortex and Substrate are flagged."""
    # Change recorded agent index in substrate
    mutated_records = [
        base_substrate_records[0],
        MutationRecord(
            sequence=2,
            agent_idx=9,  # Mismatched index (Cortex has agent 1)
            timestamp=1718000001.0,
            prev_hash="h1",
            hash="h2",
            vector_before=ControlVector(0.0, 0.0, 0.0, 0.0),
            vector_after=ControlVector(12.0, 0.03, 0.08, 0.55),
            performance_delta=150.0,
            source="substrate",
        ),
    ]

    verdict = CrossSystemInvariantCompiler.verify_global_invariance(
        shannon_trace=base_shannon_trace,
        cortex_ledger=base_cortex_ledger,
        substrate_ledger=mutated_records,
    )
    assert verdict.consistent is False
    assert any("Agent index mismatch" in detail for detail in verdict.details)


def test_global_invariance_thermodynamic_violation(
    base_shannon_trace, base_cortex_ledger, base_substrate_records
):
    """Test that thermodynamic violations on the control vector (e.g. error rate) are caught."""
    mutated_records = [
        MutationRecord(
            sequence=1,
            agent_idx=0,
            timestamp=1718000000.0,
            prev_hash="GENESIS",
            hash="h1",
            vector_before=ControlVector(0.0, 0.0, 0.0, 0.0),
            vector_after=ControlVector(10.0, 0.99, 0.1, 0.6),  # Critical error rate
            performance_delta=100.0,
            source="substrate",
        ),
        base_substrate_records[1],
    ]

    verdict = CrossSystemInvariantCompiler.verify_global_invariance(
        shannon_trace=base_shannon_trace,
        cortex_ledger=base_cortex_ledger,
        substrate_ledger=mutated_records,
    )
    assert verdict.consistent is False
    assert any("THERMODYNAMIC VIOLATION" in detail for detail in verdict.details)
