import time
import pytest
import cortex_rs


def test_accumulator_basic():
    # Instantiate the native accumulator
    acc = cortex_rs.OuroborosStateAccumulator()

    # Append state transitions
    acc.append_state("agent_0", '{"exergy": 95.0, "status": "active"}')
    acc.append_state("agent_1", '{"exergy": 88.5, "status": "active"}')
    acc.append_state("agent_2", '{"exergy": 42.0, "status": "degraded"}')

    # Retrieve the root
    root1 = acc.get_root()
    assert len(root1) == 64  # Hex encoded SHA-256 is 64 characters

    # Generate proof for agent_1
    proof = acc.get_proof("agent_1")
    assert len(proof) > 0

    # Verify the proof using the static method
    is_valid = cortex_rs.OuroborosStateAccumulator.verify_proof(
        "agent_1",
        '{"exergy": 88.5, "status": "active"}',
        proof,
        1,  # Index of agent_1
        root1,
    )
    assert is_valid is True


def test_accumulator_verify_invalid():
    acc = cortex_rs.OuroborosStateAccumulator()
    acc.append_state("agent_0", '{"val": 1}')
    acc.append_state("agent_1", '{"val": 2}')
    root = acc.get_root()

    proof = acc.get_proof("agent_0")

    # Check invalid state content fails
    is_valid = cortex_rs.OuroborosStateAccumulator.verify_proof(
        "agent_0",
        '{"val": 999}',  # Tampered state
        proof,
        0,
        root,
    )
    assert is_valid is False


def test_accumulator_performance():
    acc = cortex_rs.OuroborosStateAccumulator()

    # Load 100 agents
    for i in range(100):
        acc.append_state(f"agent_{i}", f'{{"value": {i}}}')

    root = acc.get_root()
    proof = acc.get_proof("agent_50")

    # Warmup
    for _ in range(100):
        cortex_rs.OuroborosStateAccumulator.verify_proof(
            "agent_50", '{"value": 50}', proof, 50, root
        )

    # Benchmark 10,000 operations
    iterations = 10000
    start = time.perf_counter()
    for _ in range(iterations):
        cortex_rs.OuroborosStateAccumulator.verify_proof(
            "agent_50", '{"value": 50}', proof, 50, root
        )
    elapsed = time.perf_counter() - start
    avg_duration_us = (elapsed / iterations) * 1000000

    print(f"\n[BENCHMARK] Average Verification Latency: {avg_duration_us:.4f} microseconds")
    assert avg_duration_us < 10.0, f"Average latency too high: {avg_duration_us:.4f} us"
