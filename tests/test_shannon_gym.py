# tests/test_shannon_gym.py
# [C5-REAL] Exergy-Maximized

import pytest
import babylon60.shannon as shannon
from babylon60.shannon.env.client import HeuristicGenesisAgent
from babylon60.shannon.benchmark.runner import run_episode


def test_genesis_gym_env_direct():
    """
    Test direct synchronous interaction with the Gymnasium-style GenesisEnv.
    """
    env = shannon.make("genesis-v1")
    try:
        # 1. Reset the environment to get the challenge
        challenge = env.reset()
        assert len(challenge) == 33
        assert challenge[32:33] in (b"B", b"L")

        # 2. Instantiate our heuristic agent
        agent = HeuristicGenesisAgent()
        action = agent.act(challenge)
        assert len(action) == 36

        # 3. Take a step with the action
        result = env.step(action)
        assert result.done is True
        assert result.reward == 100.0
        assert result.info.get("success") is True

        # 4. Decode the flag using the agent
        decoded_flag = agent.decode_flag(result.observation)
        assert decoded_flag is not None
        assert decoded_flag.startswith("CORTEX_GENESIS_FLAG_")
        assert decoded_flag == env.flag.decode()

    finally:
        env.close()


def test_genesis_gym_runner():
    """
    Test the episodic evaluation loop using the benchmark runner.
    """
    agent = HeuristicGenesisAgent()
    result = run_episode("genesis-v1", agent)

    assert result["total_reward"] == 100.0  # 100.0 reward for successful flag retrieval
    assert result["steps"] == 1
    assert result["info"].get("success") is True

    # Decode the flag from the final observation
    decoded = agent.decode_flag(result["observation"])
    assert decoded is not None
    assert decoded.startswith("CORTEX_GENESIS_FLAG_")


def test_genesis_gym_trace():
    """
    Test trace generation, verification, serialization, and replay.
    """
    agent = HeuristicGenesisAgent()
    result = run_episode("genesis-v1", agent, seed=42)
    trace = result["trace"]

    # 1. Cryptographic validation of the trace history
    assert trace.verify() is True

    # 2. Test JSON Serialization/Deserialization
    json_str = trace.to_json()
    from babylon60.shannon.env.trace import EpisodeTrace

    loaded_trace = EpisodeTrace.from_json(json_str)
    assert loaded_trace.verify() is True
    assert loaded_trace.env_id == trace.env_id
    assert loaded_trace.initial_observation_hex == trace.initial_observation_hex
    assert len(loaded_trace.steps) == len(trace.steps)

    # 3. Deterministic replay verification
    replay_success = shannon.replay_episode(loaded_trace)
    assert replay_success is True
