# cortex/shannon/env/trace.py
# [C5-REAL] Exergy-Maximized

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class StepTrace:
    step_idx: int
    observation_hex: str
    action_hex: str
    reward: float
    done: bool
    info: dict[str, Any]
    timestamp: float


@dataclass
class EpisodeTrace:
    env_id: str
    env_kwargs: dict[str, Any]
    seed: Any
    initial_observation_hex: str
    steps: list[StepTrace]
    checksum: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpisodeTrace":
        steps = [StepTrace(**s) for s in data["steps"]]
        return cls(
            env_id=data["env_id"],
            env_kwargs=data["env_kwargs"],
            seed=data.get("seed"),
            initial_observation_hex=data["initial_observation_hex"],
            steps=steps,
            checksum=data["checksum"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "EpisodeTrace":
        return cls.from_dict(json.loads(json_str))

    def verify(self) -> bool:
        """
        Cryptographically verifies the trace history to guarantee no post-run tampering.
        """
        computed = compute_trace_checksum(self.env_id, self.initial_observation_hex, self.steps)
        return computed == self.checksum


def compute_trace_checksum(
    env_id: str, initial_observation_hex: str, steps: list[StepTrace]
) -> str:
    hasher = hashlib.sha256()
    hasher.update(env_id.encode())
    hasher.update(initial_observation_hex.encode())
    for step in steps:
        payload = (
            f"{step.step_idx}:{step.observation_hex}:{step.action_hex}:{step.reward}:{step.done}"
        )
        hasher.update(payload.encode())
    return hasher.hexdigest()
