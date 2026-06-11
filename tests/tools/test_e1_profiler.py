"""Tests for E1Profiler.

All tests are self-contained: no live engine, no database, no network.
Traces are built from TraceBuilder fixtures.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cortex.tools.e1_profiler import ComponentStats, E1Profiler, ProfileReport
from cortex.tools.trace_builder import TraceBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_trace(trace_id: str, n_writes: int = 0, n_reads: int = 0, n_mutations: int = 0):
    b = TraceBuilder(tenant_id="t", model_version="test", op_kind="write", trace_id=trace_id)
    for _ in range(n_writes):
        b.record("write")
    for _ in range(n_reads):
        b.record("read")
    for _ in range(n_mutations):
        b.record("mutation")
    return b.build()


# ---------------------------------------------------------------------------
# ComponentStats
# ---------------------------------------------------------------------------

class TestComponentStats:
    def test_empty(self):
        s = ComponentStats.from_values([])
        assert s.mean == 0.0
        assert s.variance == 0.0

    def test_single_value(self):
        s = ComponentStats.from_values([0.5])
        assert s.mean == pytest.approx(0.5)
        assert s.variance == 0.0

    def test_two_values(self):
        s = ComponentStats.from_values([0.0, 1.0])
        assert s.mean == pytest.approx(0.5)
        assert s.variance > 0


# ---------------------------------------------------------------------------
# E1Profiler
# ---------------------------------------------------------------------------

class TestE1Profiler:
    def setup_method(self):
        # delta=1.0 only, so energy = H_branch (length-based proxy)
        self.profiler = E1Profiler(alpha=0.0, beta=0.0, gamma=0.0, delta=1.0, epsilon=0.0)

    def test_empty_corpus_returns_unknown(self):
        report = self.profiler.profile([])
        assert report.n_traces == 0
        assert report.regime == "unknown"

    def test_single_trace(self):
        t = make_trace("t1", n_writes=5)
        report = self.profiler.profile([t])
        assert report.n_traces == 1
        assert report.energy.mean >= 0.0
        assert report.energy.mean <= 1.0

    def test_shorter_traces_have_lower_mean_energy(self):
        short_traces = [make_trace(f"s{i}", n_writes=2) for i in range(10)]
        long_traces = [make_trace(f"l{i}", n_writes=50) for i in range(10)]

        r_short = self.profiler.profile(short_traces)
        r_long = self.profiler.profile(long_traces)

        assert r_short.energy.mean < r_long.energy.mean

    def test_stable_regime_for_low_energy_corpus(self):
        traces = [make_trace(f"t{i}", n_writes=1) for i in range(20)]
        report = self.profiler.profile(traces)
        assert report.regime == "stable"

    def test_report_has_all_components(self):
        traces = [make_trace("t1", n_writes=3)]
        report = self.profiler.profile(traces)
        for attr in ("D_ledger", "D_causal", "D_consensus", "H_branch", "D_proj"):
            assert hasattr(report, attr)

    def test_summary_contains_regime(self):
        traces = [make_trace("t1", n_writes=1)]
        report = self.profiler.profile(traces)
        assert "regime" in report.summary()

    def test_positive_dE_rate_zero_for_identical_traces(self):
        # All traces have same length → same energy → dE = 0 everywhere
        traces = [make_trace(f"t{i}", n_writes=5) for i in range(10)]
        report = self.profiler.profile(traces)
        assert report.positive_dE_rate == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# load_jsonl
# ---------------------------------------------------------------------------

class TestLoadJsonl:
    def test_loads_from_file(self):
        records = [
            {"id": "a", "tenant_id": "t1", "model_version": "v1", "op_kind": "write",
             "writes": 3, "reads": 1, "mutations": 0},
            {"id": "b", "tenant_id": "t2", "model_version": "v1", "op_kind": "query",
             "writes": 0, "reads": 5, "mutations": 0},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            tmp_path = Path(f.name)

        traces = E1Profiler.load_jsonl(tmp_path)
        assert len(traces) == 2
        assert traces[0].id == "a"
        assert traces[1].id == "b"
        assert traces[0].writes_count() == 3
        assert traces[1].reads_count() == 5

    def test_empty_file_returns_empty_list(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            tmp_path = Path(f.name)
        traces = E1Profiler.load_jsonl(tmp_path)
        assert traces == []

    def test_missing_file_returns_empty_list(self):
        traces = E1Profiler.load_jsonl("/nonexistent/path/traces.jsonl")
        assert traces == []
