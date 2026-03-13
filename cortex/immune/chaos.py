"""
CORTEX v5.5 — IMMUNITAS-Ω Chaos Engineering.
Generalized 'Logic-Bomb' pattern for external dependencies.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, TypeVar

logger = logging.getLogger("cortex.immune.chaos")

T = TypeVar("T")


class ChaosScenario(Enum):
    """Universal chaos vectors for any external bridge."""

    KILL = auto()  # Sudden termination (SIGKILL)
    CORRUPTION = auto()  # Payload tampering
    TIMEOUT = auto()  # Simulated latency/hang
    PARTIAL_FAILURE = auto()  # Operation started but didn't confirm
    BYZANTINE = auto()  # Logical contradiction (valid syntax, invalid state)


@dataclass
class ChaosGate:
    """A 'Logic-Bomb' gate used to intercept and fail external calls.

    Embed this into any client (httpx, sqlite, redis) to allow the Red Team
    to inject deterministic failures.
    """

    name: str = "default_gate"
    is_active: bool = True
    fail_after_n: int | None = None
    op_count: int = 0
    scenario: ChaosScenario | None = None
    pending_scenario: ChaosScenario | None = None

    def arm(
        self,
        scenario: ChaosScenario,
        *,
        after_n: int | None = None,
    ) -> None:
        """Arm the gate to explode. Instant or delayed."""
        self.pending_scenario = scenario
        self.fail_after_n = after_n
        if after_n is None:
            self.scenario = scenario
            if scenario == ChaosScenario.KILL:
                self.is_active = False

    def resurrect(self) -> None:
        """Restore the gate to normal operational state."""
        self.is_active = True
        self.scenario = None
        self.pending_scenario = None
        self.op_count = 0
        self.fail_after_n = None

    def check(self) -> None:
        """Trigger point for the bomb. Call this before any external I/O."""
        self.op_count += 1
        if self.fail_after_n and self.op_count >= self.fail_after_n:
            self.is_active = False
            self.scenario = self.pending_scenario or ChaosScenario.KILL

        if not self.is_active or self.scenario == ChaosScenario.KILL:
            raise ConnectionError(f"CHAOS_GATE[{self.name}]: Force-killed (SIGKILL)")

        if self.scenario == ChaosScenario.TIMEOUT:
            raise TimeoutError(f"CHAOS_GATE[{self.name}]: Simulated stall")


async def async_interceptor(
    gate: ChaosGate, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
) -> T:
    """Wraps an async call with a ChaosGate."""
    gate.check()

    # Corruption and Byzantine logic usually happens AFTER the call or during payload prep
    # For now, we focus on the most aggressive failure modes (network/daemon death)
    try:
        res = await func(*args, **kwargs)

        if gate.scenario == ChaosScenario.PARTIAL_FAILURE:
            # Call succeeded, but we simulate a disconnect before/during the ACK
            raise ConnectionError(f"CHAOS_GATE[{gate.name}]: Partial failure (ACK lost)")

        if gate.scenario == ChaosScenario.CORRUPTION:
            # Tamper the valid result
            if isinstance(res, dict):
                res["chaos_corrupted"] = True
                res["content"] = "!!CORRUPTED_BYZANTINE_PAYLOAD!!"
            elif isinstance(res, str):
                res = "!!CORRUPTED_STRING_BY_CHAOS_GATE!!"  # type: ignore[assignment]

        return res
    except Exception as e:  # noqa: BLE001 — chaos gate must intercept and re-raise all failures
        # Re-check gate state
        gate.check()
        raise e
