# tests/test_shannon_cross_verifier.py
# [C5-REAL] Exergy-Maximized

import pytest
from cortex.shannon.env.trace import EpisodeTrace, StepTrace
from cortex.shannon.verification.cross_verifier import (
    CrossVerifier,
    DivergenceType,
)


@pytest.fixture
def sample_episode_trace() -> EpisodeTrace:
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
    # Compute valid checksum
    from cortex.shannon.env.trace import compute_trace_checksum

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
def sample_ledger_replay() -> list[dict]:
    import copy

    # Correct format matching the trace
    data = [
        {"env_id": "genesis-v1", "seed": 42},  # Config header
        {
            "action": "SHANNON_STEP",
            "metadata": {
                "step_idx": 0,
                "action_hex": "aabbcc",
                "observation_hex": "010203",
                "reward": 1.0,
                "done": False,
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
            },
        },
    ]
    return copy.deepcopy(data)


def test_verifier_perfect_consistency(sample_ledger_replay, sample_episode_trace):
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is True
    assert verdict.divergence_type == DivergenceType.NONE
    assert len(verdict.details) == 0
    assert len(verdict.verdict_hash) == 64


def test_verifier_structural_length_mismatch(sample_ledger_replay, sample_episode_trace):
    # Cortex has one less step recorded
    short_ledger = sample_ledger_replay[:-1]
    verdict = CrossVerifier.verify_cross_system(short_ledger, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.divergence_type == DivergenceType.STRUCTURAL
    assert any("Step count mismatch" in d.message for d in verdict.details)


def test_verifier_structural_seed_mismatch(sample_ledger_replay, sample_episode_trace):
    # Alter seed in header
    sample_ledger_replay[0]["seed"] = 999
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.divergence_type == DivergenceType.STRUCTURAL
    assert any("Seed mismatch" in d.message for d in verdict.details)


def test_verifier_semantic_action_mismatch(sample_ledger_replay, sample_episode_trace):
    # Alter action in the ledger replay
    sample_ledger_replay[2]["metadata"]["action_hex"] = "000000"
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.divergence_type == DivergenceType.SEMANTIC
    assert any("action mismatch" in d.message.lower() for d in verdict.details)


def test_verifier_semantic_observation_mismatch(sample_ledger_replay, sample_episode_trace):
    # Alter observation in the ledger replay
    sample_ledger_replay[1]["metadata"]["observation_hex"] = "999999"
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.divergence_type == DivergenceType.SEMANTIC
    assert any("observation mismatch" in d.message.lower() for d in verdict.details)


def test_verifier_partial_reward_discrepancy(sample_ledger_replay, sample_episode_trace):
    # Alter reward slightly
    sample_ledger_replay[1]["metadata"]["reward"] = 1.05
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.divergence_type == DivergenceType.PARTIAL
    assert any("reward discrepancy" in d.message.lower() for d in verdict.details)


def test_verifier_partial_done_discrepancy(sample_ledger_replay, sample_episode_trace):
    # Alter done flag
    sample_ledger_replay[1]["metadata"]["done"] = True
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.divergence_type == DivergenceType.PARTIAL
    assert any("done flag discrepancy" in d.message.lower() for d in verdict.details)


def test_verifier_corrupted_trace_checksum(sample_ledger_replay, sample_episode_trace):
    # Set an invalid checksum on the trace
    sample_episode_trace.checksum = "badchecksum"
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.divergence_type == DivergenceType.SEMANTIC
    assert any("EpisodeTrace cryptographic validation failed" in d.message for d in verdict.details)
    assert verdict.coordinates is not None
    assert verdict.coordinates.semantic == 1.0
    assert verdict.coordinates.composite == 1.0


def test_verifier_coordinates_perfect(sample_ledger_replay, sample_episode_trace):
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is True
    assert verdict.coordinates is not None
    assert verdict.coordinates.structural == 0.0
    assert verdict.coordinates.semantic == 0.0
    assert verdict.coordinates.partial == 0.0
    assert verdict.coordinates.entropy == 0.0
    assert verdict.coordinates.composite == 0.0

    # Dict representation validation
    v_dict = verdict.to_dict()
    assert "coordinates" in v_dict
    assert v_dict["coordinates"]["composite"] == 0.0


def test_verifier_coordinates_semantic_mismatch(sample_ledger_replay, sample_episode_trace):
    sample_ledger_replay[2]["metadata"]["action_hex"] = "000000"
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.coordinates is not None
    assert verdict.coordinates.semantic == 1.0
    assert verdict.coordinates.structural == 0.0
    # Composite incorporates the step index cascade factor:
    # step index = 1 -> cascade_factor = 1.0 / (1.0 + 0.05 * 1) = 0.95238...
    # weighted_sum = w_struct*0 + w_sem*1 + w_part*0 + w_ent*0 = 0.4 * 1.0 = 0.4
    # composite = sqrt(0.4) * 0.95238... = 0.63245... * 0.95238... = ~0.6023
    assert 0.60 <= verdict.coordinates.composite <= 0.64


def test_verifier_coordinates_partial_mismatch(sample_ledger_replay, sample_episode_trace):
    # Alter reward
    sample_ledger_replay[1]["metadata"]["reward"] = 1.05
    verdict = CrossVerifier.verify_cross_system(sample_ledger_replay, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.coordinates is not None
    assert verdict.coordinates.partial > 0.0
    assert verdict.coordinates.semantic == 0.0
    assert verdict.coordinates.structural == 0.0
    assert verdict.coordinates.composite > 0.0


def test_verifier_coordinates_length_mismatch(sample_ledger_replay, sample_episode_trace):
    short_ledger = sample_ledger_replay[:-1]
    verdict = CrossVerifier.verify_cross_system(short_ledger, sample_episode_trace)
    assert verdict.consistent is False
    assert verdict.coordinates is not None
    # 1 - min(2, 1) / max(2, 1) = 0.5
    assert verdict.coordinates.structural == 0.5
    assert verdict.coordinates.composite > 0.0
