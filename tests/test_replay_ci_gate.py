# [C5-REAL] Exergy-Maximized
"""
Replay CI Gate Test Suite

Demuestra:
  1. Execution identity: same events → same hash chain across N runs
  2. Hash chain invariant: per-version hash equality across replicas
  3. Seed stability: different seeds produce different but internally consistent chains
  4. Gate rejects non-determinism: injected divergence triggers failure
  5. Trace generator determinism: fixed_event_trace is itself deterministic
"""

import pytest

from cortex.runtime.state import RuntimeState
from cortex.runtime.replay.ci_gate import (
    ReplayCIGate,
    ReplayCIResult,
    fixed_event_trace,
)
from cortex.runtime.replay.engine import ReplayEngine


# ── 1. Execution Identity ──────────────────────────────────────────


class TestExecutionIdentity:
    """Replay(run_n(events)) == Replay(run_m(events)) ∀ n,m"""

    def test_replay_determinism_identity(self):
        """Exact snapshot equality across 2 independent runs."""
        events = fixed_event_trace(seed=42)
        run_a = ReplayEngine(RuntimeState).run(events)
        run_b = ReplayEngine(RuntimeState).run(events)
        assert run_a == run_b

    def test_replay_determinism_identity_5_replicas(self):
        """Holds for 5 replicas — not just 2."""
        events = fixed_event_trace(seed=42)
        runs = [ReplayEngine(RuntimeState).run(events) for _ in range(5)]
        for run in runs[1:]:
            assert run == runs[0]


# ── 2. Hash Chain Invariant ─────────────────────────────────────────


class TestHashChainInvariant:
    """Per-version hash equality across replicas."""

    def test_replay_hash_chain_invariant(self):
        events = fixed_event_trace(seed=42)
        r1 = ReplayEngine(RuntimeState).run(events)
        r2 = ReplayEngine(RuntimeState).run(events)
        for s1, s2 in zip(r1, r2, strict=False):
            assert s1["state_hash"] == s2["state_hash"]

    def test_hash_chain_length_invariant(self):
        events = fixed_event_trace(seed=42, length=50)
        r1 = ReplayEngine(RuntimeState).run(events)
        r2 = ReplayEngine(RuntimeState).run(events)
        assert len(r1) == len(r2) == 51  # bootstrap + 50 events

    def test_version_monotonicity(self):
        """Versions must be strictly monotonically increasing."""
        events = fixed_event_trace(seed=42)
        snapshots = ReplayEngine(RuntimeState).run(events)
        versions = [s["version"] for s in snapshots]
        for i in range(1, len(versions)):
            assert versions[i] == versions[i - 1] + 1


# ── 3. CI Gate Programmatic Verifier ────────────────────────────────


class TestReplayCIGate:
    """The gate itself — programmatic verification."""

    def test_gate_passes_on_deterministic_state(self):
        gate = ReplayCIGate(RuntimeState, replicas=3)
        result = gate.verify(seed=42)
        assert result.passed is True
        assert result.runs_executed == 3
        assert result.divergence_point is None
        assert result.error is None

    def test_gate_passes_with_10_replicas(self):
        gate = ReplayCIGate(RuntimeState, replicas=10)
        result = gate.verify(seed=42, trace_length=30)
        assert result.passed is True
        assert result.runs_executed == 10

    def test_gate_passes_with_explicit_events(self):
        events = [
            {"action_type": "MEMORY_WRITE", "payload": {"tick": 1, "x": 100}},
            {"action_type": "MEMORY_WRITE", "payload": {"tick": 2, "y": 200}},
        ]
        gate = ReplayCIGate(RuntimeState, replicas=5)
        result = gate.verify(events=events)
        assert result.passed is True
        assert result.events_per_run == 2

    def test_gate_rejects_single_replica(self):
        with pytest.raises(ValueError, match="minimum 2"):
            ReplayCIGate(RuntimeState, replicas=1)

    def test_gate_result_to_dict(self):
        gate = ReplayCIGate(RuntimeState, replicas=2)
        result = gate.verify(seed=42)
        d = result.to_dict()
        assert d["passed"] is True
        assert isinstance(d["hash_chain_digest"], str)
        assert len(d["hash_chain_digest"]) == 16


# ── 4. Seed Stability ──────────────────────────────────────────────


class TestSeedStability:
    """Different seeds → different chains, but each seed is self-consistent."""

    def test_different_seeds_produce_different_chains(self):
        r1 = ReplayEngine(RuntimeState).run(fixed_event_trace(seed=42))
        r2 = ReplayEngine(RuntimeState).run(fixed_event_trace(seed=99))
        # Final hashes must differ (different data)
        assert r1[-1]["state_hash"] != r2[-1]["state_hash"]

    def test_same_seed_always_same_trace(self):
        t1 = fixed_event_trace(seed=42, length=10)
        t2 = fixed_event_trace(seed=42, length=10)
        assert t1 == t2

    def test_gate_stable_across_seeds(self):
        """Gate passes for any seed — determinism is seed-independent."""
        for seed in [0, 1, 42, 999, 2**16]:
            gate = ReplayCIGate(RuntimeState, replicas=3)
            result = gate.verify(seed=seed, trace_length=10)
            assert result.passed is True, f"Failed for seed={seed}: {result.error}"


# ── 5. Divergence Detection (injected non-determinism) ──────────────


class TestDivergenceDetection:
    """Gate must reject systems that lose determinism."""

    def test_gate_detects_divergent_state_class(self):
        """A state class with non-deterministic hash → gate fails."""

        class NonDeterministicState:
            _counter = 0

            def __init__(self):
                NonDeterministicState._counter += 1
                self.version = 0
                self.data = {}

            @classmethod
            def bootstrap(cls):
                return cls()

            def apply_event(self, event):
                self.version += 1
                self.data.update(event.get("payload", {}))
                return self

            def snapshot(self):
                import os

                # Inject entropy — hash includes random bytes
                noise = os.urandom(4).hex()
                return {
                    "version": self.version,
                    "state_hash": f"nondeterministic_{noise}",
                    "data": dict(self.data),
                }

        events = [
            {"action_type": "MEMORY_WRITE", "payload": {"tick": 1, "v": 1}},
        ]
        gate = ReplayCIGate(NonDeterministicState, replicas=3)
        result = gate.verify(events=events)
        assert result.passed is False
        assert result.divergence_point is not None
        assert "DIVERGENCE" in result.error
