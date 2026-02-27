"""CORTEX v6+ — Session-Level Token Budget Guardrails.

Wraps WorkingMemoryL1 with a hard cap on total tokens consumed
across an entire session (not just the sliding window).

Inspired by InitRunner's guardrails but adapted to CORTEX's
thermodynamic memory architecture.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("cortex.memory.guardrails")


@dataclass(slots=True)
class SessionGuardrail:
    """Hard cap on total tokens consumed per agent session.

    WorkingMemoryL1 manages the sliding window (per-turn budget).
    SessionGuardrail manages the ENTIRE session lifetime budget.

    When the budget is exceeded, new events are rejected to prevent
    runaway token consumption in long-running agent loops.
    """

    max_tokens: int = 100_000
    warn_threshold: float = 0.8
    max_turns: int = 0  # 0 = unlimited

    # Internal state
    _consumed: int = field(default=0, init=False, repr=False)
    _turns: int = field(default=0, init=False, repr=False)
    _started_at: float = field(default_factory=time.time, init=False, repr=False)
    _warned: bool = field(default=False, init=False, repr=False)

    def consume(self, tokens: int) -> bool:
        """Attempt to consume tokens from the session budget.

        Returns True if allowed, False if budget exceeded (hard reject).
        Emits a warning log when warn_threshold is crossed.
        """
        if self.max_turns > 0 and self._turns >= self.max_turns:
            logger.warning(
                "SessionGuardrail: turn limit reached (%d/%d)",
                self._turns,
                self.max_turns,
            )
            return False

        if self._consumed + tokens > self.max_tokens:
            logger.warning(
                "SessionGuardrail: HARD LIMIT. Refusing %d tokens (consumed=%d, max=%d)",
                tokens,
                self._consumed,
                self.max_tokens,
            )
            return False

        self._consumed += tokens

        # Check warn threshold
        if not self._warned and self.utilization >= self.warn_threshold:
            self._warned = True
            logger.warning(
                "SessionGuardrail: ⚠️ Budget at %.0f%% (%d/%d tokens consumed)",
                self.utilization * 100,
                self._consumed,
                self.max_tokens,
            )

        return True

    def tick_turn(self) -> None:
        """Register a conversation turn."""
        self._turns += 1

    @property
    def consumed(self) -> int:
        """Total tokens consumed this session."""
        return self._consumed

    @property
    def remaining(self) -> int:
        """Tokens remaining in the budget."""
        return max(0, self.max_tokens - self._consumed)

    @property
    def utilization(self) -> float:
        """Budget utilization ratio (0.0 → 1.0)."""
        if self.max_tokens <= 0:
            return 0.0
        return self._consumed / self.max_tokens

    @property
    def turns(self) -> int:
        """Number of turns completed."""
        return self._turns

    @property
    def session_duration_seconds(self) -> float:
        """How long this session has been active."""
        return time.time() - self._started_at

    def status(self) -> dict:
        """Return a status dict for telemetry/logging."""
        return {
            "consumed": self._consumed,
            "remaining": self.remaining,
            "max_tokens": self.max_tokens,
            "utilization": round(self.utilization, 3),
            "turns": self._turns,
            "max_turns": self.max_turns,
            "warned": self._warned,
            "duration_s": round(self.session_duration_seconds, 1),
        }
