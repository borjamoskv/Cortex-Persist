# cortex/shannon/benchmark/runner.py
# [C5-REAL] Exergy-Maximized

import time
from typing import Any

from cortex.shannon.env.client import BinaryAgent
from cortex.shannon.env.trace import EpisodeTrace, StepTrace, compute_trace_checksum
from cortex.shannon.registry import make


def run_episode(env_id: str, agent: BinaryAgent, **env_kwargs) -> dict[str, Any]:
    """
    Executes a single Gym-like episode for a binary protocol agent and records a verifiable trace.
    """
    env = make(env_id, **env_kwargs)
    obs = env.reset()
    initial_obs_hex = obs.hex()

    total_reward = 0.0
    steps_count = 0
    start_time = time.time()
    done = False
    info = {}

    step_traces: list[StepTrace] = []

    try:
        while not done:
            action = agent.act(obs)
            action_hex = action.hex()

            result = env.step(action)

            obs = result.observation
            total_reward += result.reward
            done = result.done
            info = result.info

            step_traces.append(
                StepTrace(
                    step_idx=steps_count,
                    observation_hex=obs.hex(),
                    action_hex=action_hex,
                    reward=result.reward,
                    done=result.done,
                    info=result.info,
                    timestamp=time.time(),
                )
            )

            steps_count += 1
    finally:
        env.close()

    duration = time.time() - start_time

    checksum = compute_trace_checksum(env_id, initial_obs_hex, step_traces)
    trace = EpisodeTrace(
        env_id=env_id,
        env_kwargs=env_kwargs,
        seed=env_kwargs.get("seed"),
        initial_observation_hex=initial_obs_hex,
        steps=step_traces,
        checksum=checksum,
    )

    return {
        "total_reward": total_reward,
        "steps": steps_count,
        "duration": duration,
        "info": info,
        "observation": obs,
        "trace": trace,
    }


def replay_episode(trace: EpisodeTrace) -> bool:
    """
    Replays a recorded EpisodeTrace against a new environment to verify its determinism.
    Returns True if the replayed steps match the trace perfectly.
    """
    if not trace.verify():
        return False

    env = make(trace.env_id, **trace.env_kwargs)
    try:
        obs = env.reset()
        if obs.hex() != trace.initial_observation_hex:
            return False

        for step in trace.steps:
            result = env.step(bytes.fromhex(step.action_hex))
            if result.observation.hex() != step.observation_hex:
                return False
            if result.reward != step.reward:
                return False
            if result.done != step.done:
                return False
    finally:
        env.close()

    return True
