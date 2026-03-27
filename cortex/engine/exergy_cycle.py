"""CORTEX v8.0 — Sovereign Exergy Cycle.

The first agent engine with an exergy frequency (derived from PULSE).
Agents don't decide when to stop. Their exergy cycle does.

High signal  → faster internal clock → deeper exploration
Low signal   → slower internal clock → automatic dormancy
Zero signal  → zero hz → graceful halt
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class CycleMetrics:
    """The agent's thermodynamic metrics at any moment."""

    clock_speed: float = 1.0  # Actions per cycle (1.0 = normal)
    entropy: float = 0.0  # Accumulated noise (high = halt)
    signal: float = 1.0  # Useful output ratio (0-1)
    temperature: float = 0.5  # Exploration vs exploitation
    cycles: int = 0  # Total execution cycles
    peak_signal: float = 0.0  # Best signal ever recorded


class ExergyCycle:
    """The self-regulating exergy cycle engine.

    Measures the DELTA between world states after each action.
    If the delta is meaningful → signal rises → agent accelerates.
    If the delta is noise → entropy rises → agent decelerates.
    When entropy > signal → halt → agent stops.
    """

    def __init__(self, halt_threshold: float = 3.0) -> None:
        self.metrics = CycleMetrics()
        self.halt_threshold = halt_threshold
        self.state_hashes: list[str] = []
        self.history: list[dict[str, Any]] = []

    @property
    def active(self) -> bool:
        """The agent runs while its signal exceeds its entropy."""
        return self.metrics.entropy < self.halt_threshold and self.metrics.signal > 0.05

    @property
    def frequency(self) -> str:
        """Human-readable processing frequency."""
        hz = self.metrics.clock_speed
        if hz > 1.5:
            return "⚡ OVERCLOCK"
        if hz > 0.8:
            return "🟢 NOMINAL"
        if hz > 0.3:
            return "🟡 THROTTLED"
        return "🔴 HALTED"

    def _hash_state(self, state: str) -> str:
        return hashlib.md5(state.encode("utf-8")).hexdigest()[:12]

    def synthesize(self, observation: str, action_type: str = "action") -> dict[str, Any]:
        """The core exergy cycle. Called after every action.

        Args:
            observation: The text output or state observed after the action.
            action_type: What kind of action triggered this (e.g. "tool_call", "thought").

        Returns:
            Diagnostic dictionary of current exergy metrics.
        """
        self.metrics.cycles += 1
        state_hash = self._hash_state(observation)

        # ── Signal Detection ──
        # If the world state changed meaningfully → signal
        # If we've seen this state before → entropy
        is_novel = state_hash not in self.state_hashes
        self.state_hashes.append(state_hash)

        # Signal decays continuously
        if is_novel:
            self.metrics.signal = min(1.0, self.metrics.signal + 0.2)
            self.metrics.entropy = max(0.0, self.metrics.entropy - 0.1)
        else:
            self.metrics.signal = max(0.0, self.metrics.signal - 0.15)
            if action_type != "think":
                self.metrics.entropy += 0.4  # Repetition is toxic for actions

        # ── Entropy Grace Period (Ω₅: Antifragile by Default) ──
        # "think" actions signal strategy reconsideration.
        # Reflecting IS progress — reward it with partial entropy forgiveness.
        # Only penalize thoughts that are both repeated AND non-novel.
        if action_type == "think":
            if is_novel:
                # Novel thought = genuine reflection = entropy forgiveness
                self.metrics.entropy *= 0.7  # 30% grace
            else:
                # Repeated thought = rumination = mild penalty (less than action)
                self.metrics.entropy += 0.1  # Was 0.2, now gentler

        # ── Clock Speed Adjustment ──
        # High signal → explore more aggressively
        # Low signal → conserve energy
        self.metrics.clock_speed = 0.5 + (self.metrics.signal * 1.5)

        # ── Temperature (exploration tendency) ──
        self.metrics.temperature = max(
            0.1, min(0.9, 0.3 + (self.metrics.signal * 0.6) - (self.metrics.entropy * 0.1))
        )

        # ── Peak tracking ──
        self.metrics.peak_signal = max(self.metrics.peak_signal, self.metrics.signal)

        diagnostic = {
            "cycle": self.metrics.cycles,
            "hz": self.frequency,
            "signal": round(self.metrics.signal, 2),
            "entropy": round(self.metrics.entropy, 2),
            "temperature": round(self.metrics.temperature, 2),
            "novel": is_novel,
            "active": self.active,
        }
        self.history.append(diagnostic)
        return diagnostic

    def render_metrics(self, diag: dict[str, Any] | None = None) -> str:
        """Render a visual representation of current exergy bounds."""
        m = self.metrics
        d = diag or {}
        return (
            f"┌─ CYCLE METRICS ──────────────────────┐\n"
            f"│ Cycle: {m.cycles:>3}      {self.frequency:>20} │\n"
            f"│ Signal:  {'█' * int(m.signal * 10):.<10} {m.signal:.2f}        │\n"
            f"│ Entropy: {'░' * int(m.entropy * 3):.<10} {m.entropy:.2f}        │\n"
            f"│ Temp:    {m.temperature:.2f}                       │\n"
            f"│ Novel:   {str(d.get('novel', '?')):<5}                       │\n"
            f"└──────────────────────────────────────┘"
        )


class CapitalExergyReactor:
    """Sovereign Capital Autocatalytic Engine. (Ouroboros-Taint)

    Consumes capitalism inbound yield and autonomously allocates capital vectors
    towards Swarm scaling cryptographically securely.
    """

    def __init__(self, bus: Any, reinvest_ratio: float = 0.176) -> None:
        self.bus = bus
        self.reinvest_ratio = reinvest_ratio

    async def absorb_fiat_yield(self, amount: float, source: str, currency: str = "EUR") -> float:
        """Process inbound capital, cryptographic commit, and yield the reinvest amount."""
        reinvest = round(amount * self.reinvest_ratio, 2)

        from cortex.agents.message_schema import MessageKind, new_message

        msg = new_message(
            sender="exergy_cycle.capital",
            recipient="mercor-autodidact-omega",
            kind=MessageKind.CAPITAL_REINVEST,
            payload={
                "amount": reinvest,
                "currency": currency,
                "parent_source": source,
                "action": "AUTO_YIELD_SPLIT",
            },
        )

        # Transmit the exergy payload to the Agent Bus
        await self.bus.broadcast(msg)
        return reinvest
