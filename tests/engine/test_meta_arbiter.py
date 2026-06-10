"""Tests for MetaArbiterKernel over ExecutionTrace.

These tests are intentionally self-contained:
- No live engine
- No database
- No consensus or causality wiring

They verify that the MetaArbiterKernel can:
- Compute non-negative energy values
- Distinguish traces by a simple H_branch proxy
- Select the lowest-energy trajectory as the winner
"""
from __future__ import annotations

from dataclasses import dataclass

from cortex.engine.meta_arbiter import MetaArbiterKernel
from cortex.tools.trace_builder import TraceBuilder


# ---------------------------------------------------------------------------
# Dummy state containers
# ---------------------------------------------------------------------------

@dataclass
class DummyState:
    id: str = "state-0"


class DummyGraph:
    pass


class DummyVoteLedger:
    pass


class DummyReplayEngine:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_trace(trace_id: str, n_events: int) -> tuple:
    """Build a simple trace with `n_events` writes.

    The MetaArbiterKernel's H_branch proxy will assign higher energy
    to traces with more events when delta > 0.
    """

    b = TraceBuilder(tenant_id="t", model_version="test", op_kind="write", trace_id=trace_id)
    for _ in range(n_events):
        b.record("write")
    return b.build()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMetaArbiterKernel:
    def setup_method(self):
        self.kernel = MetaArbiterKernel(alpha=0.0, beta=0.0, gamma=0.0, epsilon=0.0, delta=1.0)
        self.state = DummyState()
        self.graph = DummyGraph()
        self.vote_ledger = DummyVoteLedger()
        self.replay_engine = DummyReplayEngine()

    def test_score_non_negative(self):
        trace = make_trace("t-1", 5)
        sc = self.kernel.score(
            trace,
            state=self.state,
            causal_graph=self.graph,
            vote_ledger=self.vote_ledger,
            replay_engine=self.replay_engine,
        )
        assert sc.energy >= 0.0
        assert 0.0 <= sc.H_branch <= 1.0

    def test_shorter_trace_has_lower_energy(self):
        t_short = make_trace("short", 5)
        t_long = make_trace("long", 50)

        futures = [t_long, t_short]
        winner, receipt = self.kernel.collapse(
            futures,
            state=self.state,
            causal_graph=self.graph,
            vote_ledger=self.vote_ledger,
            replay_engine=self.replay_engine,
        )

        assert winner is not None
        assert winner.id == "short"

        e_short = receipt.scores["short"].energy
        e_long = receipt.scores["long"].energy
        assert e_short <= e_long

    def test_collapse_empty_returns_none(self):
        winner, receipt = self.kernel.collapse(
            [],
            state=self.state,
            causal_graph=self.graph,
            vote_ledger=self.vote_ledger,
            replay_engine=self.replay_engine,
        )
        assert winner is None
        assert receipt.winning_id == ""
        assert receipt.scores == {}

    def test_state_snapshot_prefers_id(self):
        trace = make_trace("t-2", 1)
        _, receipt = self.kernel.collapse(
            [trace],
            state=self.state,
            causal_graph=self.graph,
            vote_ledger=self.vote_ledger,
            replay_engine=self.replay_engine,
        )
        assert receipt.state_snapshot == "state-0"
