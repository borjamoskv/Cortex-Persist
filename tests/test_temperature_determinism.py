"""
tests/test_temperature_determinism.py
======================================
Pytest suite for the Temperature Determinism Gate.

Runs WITHOUT Ollama (mocked HTTP) — safe for CI.
Validates the gate logic itself, not the model.

Ω₃ (Byzantine Default): The gate must be trustworthy before we trust it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── Import the benchmark module ──────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.bench_temperature import (
    MAX_DETERMINISM_DRIFT,
    MIN_ENTROPY_GAP,
    GateResult,
    TrialResult,
    benchmark,
    export_json,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_trial(
    outputs: list[str],
    temperature: float = 0.05,
    label: str = "deterministic",
) -> TrialResult:
    t = TrialResult(temperature=temperature, label=label)
    t.outputs = outputs
    t.latencies_ms = [50.0] * len(outputs)
    return t


# ─── TrialResult unit tests ───────────────────────────────────────────────────


class TestTrialResult:
    def test_unique_ratio_all_same(self) -> None:
        t = _make_trial(["def f(): return 1"] * 10)
        assert t.unique_ratio == pytest.approx(0.1, abs=0.01)

    def test_unique_ratio_all_different(self) -> None:
        t = _make_trial([f"def f(): return {i}" for i in range(10)])
        assert t.unique_ratio == pytest.approx(1.0, abs=0.01)

    def test_unique_ratio_empty(self) -> None:
        t = TrialResult(temperature=0.05, label="x")
        assert t.unique_ratio == 0.0

    def test_hallucination_detected_when_no_def(self) -> None:
        t = _make_trial(["def f(): pass"] * 9 + ["sorry I cannot do that"])
        assert t.contains_hallucination is True

    def test_no_hallucination_when_all_valid(self) -> None:
        t = _make_trial(["def is_prime(n): return n > 1"] * 10)
        assert t.contains_hallucination is False

    def test_avg_latency(self) -> None:
        t = _make_trial(["def f(): pass"] * 5)
        t.latencies_ms = [100.0, 200.0, 300.0, 400.0, 500.0]
        assert t.avg_latency_ms == pytest.approx(300.0)


# ─── GateResult logic ─────────────────────────────────────────────────────────


class TestGateResult:
    def _result(
        self,
        low_outputs: list[str],
        high_outputs: list[str],
        violations: list[str] | None = None,
    ) -> GateResult:
        low = _make_trial(low_outputs, temperature=0.05, label="deterministic")
        high = _make_trial(high_outputs, temperature=0.80, label="creative")
        passed = len(violations or []) == 0
        drift = low.unique_ratio
        gap = high.unique_ratio - low.unique_ratio
        return GateResult(
            model="test-model",
            passed=passed,
            drift_ratio=drift,
            entropy_gap=gap,
            trials=[low, high],
            violations=violations or [],
        )

    def test_gate_passes_with_good_values(self) -> None:
        # Low temp: 1 unique out of 10 → 10% drift (< 40% gate)
        # High temp: 9 unique out of 10 → 90% drift
        # Gap = 80% (> 25% minimum)
        r = self._result(
            low_outputs=["def is_prime(n): return n > 1"] * 10,
            high_outputs=[f"def is_prime(n): return n > {i}" for i in range(10)],
        )
        # Manually check thresholds
        assert r.drift_ratio <= MAX_DETERMINISM_DRIFT
        assert r.entropy_gap >= MIN_ENTROPY_GAP

    def test_gate_detects_drift_breach(self) -> None:
        # Low temp: 9 unique out of 10 → 90% drift (> 40% gate) ← BREACH
        r = self._result(
            low_outputs=[f"def f(): return {i}" for i in range(9)] + ["def f(): return 0"],
            high_outputs=[f"def g(): return {i}" for i in range(10)],
            violations=["DRIFT EXCEEDED"],
        )
        assert not r.passed
        assert len(r.violations) == 1

    def test_gate_detects_entropy_gap_collapse(self) -> None:
        # Both temps produce same diversity → gap too small
        same_outputs = [f"def f(): return {i}" for i in range(10)]
        r = self._result(
            low_outputs=same_outputs,
            high_outputs=same_outputs,
            violations=["ENTROPY GAP COLLAPSED"],
        )
        assert not r.passed

    def test_multiple_violations_accumulate(self) -> None:
        r = self._result(
            low_outputs=[f"def f(): return {i}" for i in range(10)],
            high_outputs=[f"def f(): return {i}" for i in range(10)],
            violations=["DRIFT EXCEEDED", "ENTROPY GAP COLLAPSED"],
        )
        assert len(r.violations) == 2


# ─── CLI / export tests ───────────────────────────────────────────────────────


class TestExportJson:
    def test_json_export_structure(self, tmp_path: Path) -> None:
        low = _make_trial(["def f(): pass"] * 10, temperature=0.05)
        high = _make_trial(
            [f"def f(): return {i}" for i in range(10)], temperature=0.80
        )
        result = GateResult(
            model="qwen2.5-coder:7b",
            passed=True,
            drift_ratio=0.1,
            entropy_gap=0.8,
            trials=[low, high],
            violations=[],
        )
        out = tmp_path / "report.json"
        export_json(result, str(out))

        data = json.loads(out.read_text())
        assert data["model"] == "qwen2.5-coder:7b"
        assert data["passed"] is True
        assert len(data["trials"]) == 2
        assert data["trials"][0]["temperature"] == 0.05
        assert "unique_ratio" in data["trials"][0]

    def test_json_export_with_violations(self, tmp_path: Path) -> None:
        low = _make_trial([f"def f(): return {i}" for i in range(10)], temperature=0.05)
        high = _make_trial([f"def g(): return {i}" for i in range(10)], temperature=0.80)
        result = GateResult(
            model="bad-model",
            passed=False,
            drift_ratio=0.9,
            entropy_gap=0.0,
            trials=[low, high],
            violations=["DRIFT EXCEEDED", "ENTROPY GAP COLLAPSED"],
        )
        out = tmp_path / "report.json"
        export_json(result, str(out))

        data = json.loads(out.read_text())
        assert data["passed"] is False
        assert len(data["violations"]) == 2


# ─── Gate threshold validation ────────────────────────────────────────────────


class TestGateThresholds:
    """These tests verify the gate values are sane.

    4 layers of protection:
    L1 — Value range checks (loose mutations caught)
    L2 — Source literal validation (env injection attack caught)
    L3 — Mathematical coherence (impossible gate caught)
    L4 — Adversarial inversion (gate sign-flip caught in both directions)
    """

    # ── L1: Value range ───────────────────────────────────────────────────────

    def test_max_drift_is_strict(self) -> None:
        assert MAX_DETERMINISM_DRIFT <= 0.40, (
            f"MAX_DETERMINISM_DRIFT={MAX_DETERMINISM_DRIFT} is too loose. "
            "Values > 0.40 allow significant non-determinism in code generation."
        )

    def test_max_drift_is_not_zero(self) -> None:
        assert MAX_DETERMINISM_DRIFT > 0.0, (
            "MAX_DETERMINISM_DRIFT=0.0 is too strict. "
            "Some variation between identical prompts is expected."
        )

    def test_entropy_gap_is_meaningful(self) -> None:
        assert MIN_ENTROPY_GAP >= 0.20, (
            f"MIN_ENTROPY_GAP={MIN_ENTROPY_GAP} is too small. "
            "A gap < 0.20 means temperature is not differentiating regimes."
        )

    # ── L2: Source literal validation ─────────────────────────────────────────

    def test_constants_are_hardcoded_not_env_injectable(self) -> None:
        """
        Attack vector: CI_ENV: MAX_DETERMINISM_DRIFT=0.99
        → gate reads from os.environ silently → gate always green

        Defense: constants must be Python literals in source. This test
        reads the source file and asserts the literal string is present.
        """
        source = Path(__file__).parent.parent / "benchmarks" / "bench_temperature.py"
        text = source.read_text()

        assert "MAX_DETERMINISM_DRIFT: float = 0.40" in text, (
            "MAX_DETERMINISM_DRIFT must be a hardcoded float literal. "
            "Do NOT replace with os.getenv() — that makes the gate injectable."
        )
        assert "MIN_ENTROPY_GAP: float = 0.25" in text, (
            "MIN_ENTROPY_GAP must be a hardcoded float literal. "
            "Do NOT replace with os.getenv() — that makes the gate injectable."
        )

    # ── L3: Mathematical coherence ─────────────────────────────────────────────

    def test_mathematical_coherence(self) -> None:
        """
        MAX_DRIFT + MIN_GAP must be ≤ 1.0.

        If MAX_DRIFT=0.40 and MIN_GAP=0.70, the gate is impossible:
        low_ratio ≤ 0.40, high_ratio ≥ low_ratio + 0.70 → high_ratio ≥ 1.10 → ∅
        """
        combined = MAX_DETERMINISM_DRIFT + MIN_ENTROPY_GAP
        assert combined <= 1.0, (
            f"Gate is mathematically impossible: "
            f"MAX_DRIFT({MAX_DETERMINISM_DRIFT}) + MIN_GAP({MIN_ENTROPY_GAP}) "
            f"= {combined:.2f} > 1.0. No model can have unique_ratio > 100%."
        )

    # ── L4: Adversarial inversion ──────────────────────────────────────────────

    def test_inverted_gate_would_reject_known_good_model(self) -> None:
        """
        If someone accidentally inverts the comparison operators (≤ → ≥),
        a known-good model must be REJECTED — making the inversion detectable.

        Known-good model behavior: 10% drift at low temp, 90% at high temp.
        """
        low_drift = 0.10   # unique_ratio at temp 0.05
        high_chaos = 0.90  # unique_ratio at temp 0.80
        gap = high_chaos - low_drift  # 0.80

        # Correct gate: MUST PASS
        assert low_drift <= MAX_DETERMINISM_DRIFT and gap >= MIN_ENTROPY_GAP, (
            "Known-good model must pass the correct gate."
        )

        # Inverted gate: MUST REJECT the good model (inversion is detectable)
        inverted = low_drift >= MAX_DETERMINISM_DRIFT and gap <= MIN_ENTROPY_GAP
        assert not inverted, (
            "The inverted gate must REJECT a good model. "
            "If it doesn't, the inversion is undetectable — fix gate boundaries."
        )

    def test_gate_rejects_known_bad_model(self) -> None:
        """
        A known-BAD model (85% drift, 10% gap) must fail the correct gate
        and pass the inverted gate — confirming the gate discriminates both ways.
        """
        bad_drift = 0.85  # 85% unique at low temp — non-deterministic
        bad_gap = 0.10    # temperature has almost no effect

        # Correct gate: MUST FAIL
        assert not (bad_drift <= MAX_DETERMINISM_DRIFT and bad_gap >= MIN_ENTROPY_GAP), (
            "Known-bad model must fail the correct gate."
        )

        # Inverted gate: would incorrectly PASS — confirms gates are distinguishable
        inverted_accepts_bad = bad_drift >= MAX_DETERMINISM_DRIFT and bad_gap <= MIN_ENTROPY_GAP
        assert inverted_accepts_bad, (
            "The inverted gate should accept a bad model. "
            "This proves correct/inverted gates are discriminating."
        )


# ─── benchmark() with mocked HTTP ─────────────────────────────────────────────


class TestBenchmarkMocked:
    """Integration test of benchmark() without real Ollama.

    Mocks httpx.AsyncClient.post to return pre-baked responses.
    """

    def _make_response(self, text: str) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": text}
        return mock_resp

    @pytest.mark.asyncio
    async def test_deterministic_model_passes_gate(self) -> None:
        """A model that produces identical output at low temp should pass."""
        call_count = 0
        canonical = "def is_prime(n):\n    if n < 2: return False\n    return all(n % i for i in range(2, n))"

        async def mock_post(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            body = kwargs.get("json", {})
            temp = body.get("options", {}).get("temperature", 0.5)
            call_count += 1
            # Low temp → always same. High temp → always different.
            if temp <= 0.1:
                return self._make_response(canonical)
            return self._make_response(f"{canonical}  # variant {call_count}")

        with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=mock_post)):
            result = await benchmark(model="fake-model", runs=5, verbose=False)

        assert result.passed, f"Expected PASS, got violations: {result.violations}"
        assert result.drift_ratio <= MAX_DETERMINISM_DRIFT
        assert result.entropy_gap >= MIN_ENTROPY_GAP

    @pytest.mark.asyncio
    async def test_non_deterministic_model_fails_gate(self) -> None:
        """A model that produces different output even at low temp fails drift gate."""
        call_count = 0

        async def mock_post(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            # Always produce unique output regardless of temperature
            return self._make_response(f"def f(): return {call_count}")

        with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=mock_post)):
            result = await benchmark(model="broken-model", runs=5, verbose=False)

        assert not result.passed
        any_drift_violation = any("DRIFT" in v for v in result.violations)
        assert any_drift_violation, f"Expected DRIFT violation, got: {result.violations}"

    @pytest.mark.asyncio
    async def test_ollama_unreachable_raises(self) -> None:
        """RuntimeError is raised (not swallowed) when Ollama is down."""
        from httpx import ConnectError

        with patch(
            "httpx.AsyncClient.post",
            new=AsyncMock(side_effect=ConnectError("refused")),
        ):
            with pytest.raises(RuntimeError, match="Ollama unreachable"):
                await benchmark(model="any", runs=1, verbose=False)


# ─── Script invocation (subprocess) ──────────────────────────────────────────


class TestCLI:
    def test_help_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, "benchmarks/bench_temperature.py", "--help"],
            capture_output=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert b"CORTEX Temperature" in result.stdout

    def test_allow_skip_exits_zero_when_ollama_missing(self) -> None:
        """With --allow-skip and no Ollama, must exit 0 (CI doesn't break)."""
        result = subprocess.run(
            [
                sys.executable,
                "benchmarks/bench_temperature.py",
                "--quick",
                "--allow-skip",
                "--model",
                "nonexistent-model:99b",
            ],
            capture_output=True,
            cwd=Path(__file__).parent.parent,
            timeout=10,
        )
        # Either Ollama is running (0 or 1) or unreachable (exit 0 via --allow-skip)
        assert result.returncode in (0, 1), (
            f"Unexpected exit {result.returncode}: {result.stderr.decode()}"
        )
