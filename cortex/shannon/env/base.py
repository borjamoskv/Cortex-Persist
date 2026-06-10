# cortex/shannon/env/base.py
# [C5-REAL] Exergy-Maximized

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class StepResult:
    observation: bytes
    reward: float
    done: bool
    info: dict


class BinaryEnv(ABC):
    """
    Gym-like environment for binary protocol agents.
    Observation = raw bytes stream (not tokenized).
    """

    @abstractmethod
    def reset(self) -> bytes:
        """Start episode, return initial observation"""
        pass

    @abstractmethod
    def step(self, action: bytes) -> StepResult:
        """Send binary action, receive next state"""
        pass

    @abstractmethod
    def close(self):
        """Clean up environment resources"""
        pass
