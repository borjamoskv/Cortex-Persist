"""CORTEX v8.0 — Sovereign Biological Metabolism.

The first agent engine with a heartbeat (derived from PULSE).
Agents don't decide when to stop. Their metabolism does.

High signal  → faster pulse → deeper exploration
Low signal   → slower pulse → automatic dormancy
Zero signal  → flatline → graceful death
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class Vitals:
    """The agent's vital signs at any moment."""

    heart_rate: float = 1.0  # Actions per cycle (1.0 = normal)
    entropy: float = 0.0  # Accumulated noise (high = dying)
    signal: float = 1.0  # Useful output ratio (0-1)
    temperature: float = 0.5  # Exploration vs exploitation
    age: int = 0  # Total heartbeats
    peak_signal: float = 0.0  # Best signal ever recorded


class Metabolism:
    """The self-regulating metabolic engine.

    Measures the DELTA between world states after each action.
    If the delta is meaningful → signal rises → agent accelerates.
    If the delta is noise → entropy rises → agent decelerates.
    When entropy > signal → flatline → agent stops.
    """

    def __init__(self, flatline_threshold: float = 3.0) -> None:
        self.vitals = Vitals()
        self.flatline_threshold = flatline_threshold
        self.state_hashes: list[str] = []
        self.history: list[dict[str, Any]] = []

    @property
    def alive(self) -> bool:
        """The agent lives while its signal exceeds its entropy."""
        return self.vitals.entropy < self.flatline_threshold and self.vitals.signal > 0.05

    @property
    def bpm(self) -> str:
        """Human-readable heart rate."""
        hr = self.vitals.heart_rate
        if hr > 1.5:
            return "🫀 TACHYCARDIA"
        if hr > 0.8:
            return "💚 NORMAL"
        if hr > 0.3:
            return "💛 BRADYCARDIA"
        return "🔴 FLATLINE"

    def _hash_state(self, state: str) -> str:
        return hashlib.md5(state.encode("utf-8")).hexdigest()[:12]

    def metabolize(self, observation: str, action_type: str = "action") -> dict[str, Any]:
        """The core metabolic cycle. Called after every action.

        Args:
            observation: The text output or state observed after the action.
            action_type: What kind of action triggered this (e.g. "tool_call", "thought").

        Returns:
            Diagnostic dictionary of current vitals.
        """
        self.vitals.age += 1
        state_hash = self._hash_state(observation)

        # ── Signal Detection ──
        # If the world state changed meaningfully → signal
        # If we've seen this state before → entropy
        is_novel = state_hash not in self.state_hashes
        self.state_hashes.append(state_hash)

        # Signal decays naturally (like real metabolism)
        if is_novel:
            self.vitals.signal = min(1.0, self.vitals.signal + 0.2)
            self.vitals.entropy = max(0.0, self.vitals.entropy - 0.1)
        else:
            self.vitals.signal = max(0.0, self.vitals.signal - 0.15)
            self.vitals.entropy += 0.4  # Repetition is toxic

        # ── Entropy Grace Period (Ω₅: Antifragile by Default) ──
        # "think" actions signal strategy reconsideration.
        # Reflecting IS progress — reward it with partial entropy forgiveness.
        # Only penalize thoughts that are both repeated AND non-novel.
        if action_type == "think":
            if is_novel:
                # Novel thought = genuine reflection = entropy forgiveness
                self.vitals.entropy *= 0.7  # 30% grace
            else:
                # Repeated thought = rumination = mild penalty (less than action)
                self.vitals.entropy += 0.1  # Was 0.2, now gentler

        # ── Heart Rate Adjustment ──
        # High signal → explore more aggressively
        # Low signal → conserve energy
        self.vitals.heart_rate = 0.5 + (self.vitals.signal * 1.5)

        # ── Temperature (exploration tendency) ──
        self.vitals.temperature = max(
            0.1, min(0.9, 0.3 + (self.vitals.signal * 0.6) - (self.vitals.entropy * 0.1))
        )

        # ── Peak tracking ──
        self.vitals.peak_signal = max(self.vitals.peak_signal, self.vitals.signal)

        diagnostic = {
            "beat": self.vitals.age,
            "bpm": self.bpm,
            "signal": round(self.vitals.signal, 2),
            "entropy": round(self.vitals.entropy, 2),
            "temperature": round(self.vitals.temperature, 2),
            "novel": is_novel,
            "alive": self.alive,
        }
        self.history.append(diagnostic)
        return diagnostic

    def render_vitals(self, diag: dict[str, Any] | None = None) -> str:
        """Render a visual representation of current vitals."""
        v = self.vitals
        d = diag or {}
        return (
            f"┌─ VITALS ─────────────────────────────┐\n"
            f"│ Beat: {v.age:>3}        {self.bpm:>20} │\n"
            f"│ Signal:  {'█' * int(v.signal * 10):.<10} {v.signal:.2f}        │\n"
            f"│ Entropy: {'░' * int(v.entropy * 3):.<10} {v.entropy:.2f}        │\n"
            f"│ Temp:    {v.temperature:.2f}                       │\n"
            f"│ Novel:   {str(d.get('novel', '?')):<5}                       │\n"
            f"└──────────────────────────────────────┘"
        )
