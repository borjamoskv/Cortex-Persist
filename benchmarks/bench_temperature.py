"""
benchmarks/bench_temperature.py
================================
CORTEX Temperature Determinism Benchmark — Ω₃ (Byzantine Default)

Gate: if unique_ratio at temp ≤ 0.1 exceeds MAX_DETERMINISM_DRIFT,
the model has degraded and MUST NOT enter the production stack.

Usage:
    # Full benchmark (requires Ollama running locally):
    python benchmarks/bench_temperature.py

    # Quick gate check (fewer runs, fast CI feedback):
    python benchmarks/bench_temperature.py --quick

    # Custom model:
    python benchmarks/bench_temperature.py --model qwen2.5-coder:7b --runs 5

Exit codes:
    0  — All determinism gates passed
    1  — One or more gates FAILED (model degraded, block from production)
    2  — Ollama unreachable (skip gracefully in CI with --allow-skip)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field

import httpx

# ─── Config ───────────────────────────────────────────────────────────────────

OLLAMA_BASE = "http://localhost:11434"

# Determinism gate: unique_ratio at LOW_TEMP must stay BELOW this threshold.
# > 0.40 means the model is producing 40%+ distinct outputs on a deterministic
# task — a clear signal of thermal collapse or quantisation degradation.
MAX_DETERMINISM_DRIFT: float = 0.40

# Entropy gap: LOW_TEMP uniqueness must be at least this LOWER than HIGH_TEMP.
# If the gap closes, the temperature knob has lost meaning (model is broken).
MIN_ENTROPY_GAP: float = 0.25

CODE_PROBE = """\
Implement a Python function that returns True if a number is prime, False otherwise.
Return ONLY the function. No imports. No explanation. No docstring.
"""

TEMPERATURE_PAIRS = [
    (0.05, "deterministic"),
    (0.80, "creative"),
]


# ─── Data Types ───────────────────────────────────────────────────────────────


@dataclass
class TrialResult:
    temperature: float
    label: str
    outputs: list[str] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def unique_ratio(self) -> float:
        if not self.outputs:
            return 0.0
        return len(set(self.outputs)) / len(self.outputs)

    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def contains_hallucination(self) -> bool:
        """Heuristic: valid Python function must contain 'def '."""
        return any("def " not in o for o in self.outputs)


@dataclass
class GateResult:
    model: str
    passed: bool
    drift_ratio: float  # unique_ratio at low temp
    entropy_gap: float  # high_ratio - low_ratio
    trials: list[TrialResult]
    violations: list[str]


# ─── Core ─────────────────────────────────────────────────────────────────────


async def _probe_once(
    client: httpx.AsyncClient,
    model: str,
    temperature: float,
    ctx: int = 2048,
) -> tuple[str, float]:
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{OLLAMA_BASE}/api/generate",
            json={
                "model": model,
                "prompt": CODE_PROBE,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": ctx,
                    "seed": -1,  # No fixed seed — pure model randomness
                },
            },
        )
        resp.raise_for_status()
        elapsed = (time.perf_counter() - t0) * 1000
        return resp.json()["response"].strip(), elapsed

    except httpx.ConnectError as exc:
        raise RuntimeError(f"Ollama unreachable at {OLLAMA_BASE}") from exc


async def run_trial(
    client: httpx.AsyncClient,
    model: str,
    temperature: float,
    label: str,
    runs: int,
    *,
    verbose: bool = True,
) -> TrialResult:
    trial = TrialResult(temperature=temperature, label=label)

    if verbose:
        print(f"\n  🔬 temp={temperature} ({label}) — {runs} runs...")

    for i in range(runs):
        output, ms = await _probe_once(client, model, temperature)
        trial.outputs.append(output)
        trial.latencies_ms.append(ms)
        if verbose:
            print(f"     run {i + 1:02d} | {ms:6.0f}ms | {len(output):4d} chars", flush=True)

    return trial


async def benchmark(
    model: str,
    runs: int,
    *,
    verbose: bool = True,
) -> GateResult:
    trials: list[TrialResult] = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
        for temp, label in TEMPERATURE_PAIRS:
            t = await run_trial(client, model, temp, label, runs, verbose=verbose)
            trials.append(t)

    low_trial = trials[0]  # temp 0.05
    high_trial = trials[1]  # temp 0.80

    drift = low_trial.unique_ratio
    gap = high_trial.unique_ratio - low_trial.unique_ratio

    violations: list[str] = []

    if drift > MAX_DETERMINISM_DRIFT:
        violations.append(
            f"DRIFT EXCEEDED: unique_ratio at temp {low_trial.temperature} "
            f"= {drift:.0%} > {MAX_DETERMINISM_DRIFT:.0%} gate"
        )

    if gap < MIN_ENTROPY_GAP:
        violations.append(
            f"ENTROPY GAP COLLAPSED: high_ratio - low_ratio = {gap:.0%} "
            f"< {MIN_ENTROPY_GAP:.0%} minimum"
        )

    if low_trial.contains_hallucination:
        violations.append(
            f"HALLUCINATION DETECTED: at temp {low_trial.temperature}, "
            f"at least one output lacked a valid function signature"
        )

    return GateResult(
        model=model,
        passed=len(violations) == 0,
        drift_ratio=drift,
        entropy_gap=gap,
        trials=trials,
        violations=violations,
    )


# ─── Report ───────────────────────────────────────────────────────────────────


def print_report(result: GateResult) -> None:
    status = "✅ PASSED" if result.passed else "❌ FAILED"
    bar = "═" * 62

    print(f"\n{bar}")
    print(f"  TEMPERATURE DETERMINISM GATE — {result.model}")
    print(bar)

    for t in result.trials:
        hall = "🔥 YES" if t.contains_hallucination else "✅ no"
        print(f"""
  temp={t.temperature} ({t.label})
  ├─ unique outputs   : {t.unique_ratio:.0%}  ({len(set(t.outputs))}/{len(t.outputs)})
  ├─ avg latency      : {t.avg_latency_ms:.0f}ms
  └─ hallucination    : {hall}""")

    print(f"""
  ──────────────────────────────────────────────────────────
  Δ unique_ratio (high - low) : {result.entropy_gap:+.0%}
  Drift gate (low ≤ {MAX_DETERMINISM_DRIFT:.0%})        : {"OK" if result.drift_ratio <= MAX_DETERMINISM_DRIFT else "BREACH"}
  Entropy gap (Δ ≥ {MIN_ENTROPY_GAP:.0%})        : {"OK" if result.entropy_gap >= MIN_ENTROPY_GAP else "BREACH"}
  ──────────────────────────────────────────────────────────
  Result: {status}""")

    if result.violations:
        print("\n  VIOLATIONS:")
        for v in result.violations:
            print(f"    ✗ {v}")

    print(f"\n{bar}\n")


def export_json(result: GateResult, path: str) -> None:
    payload = {
        "model": result.model,
        "passed": result.passed,
        "drift_ratio": result.drift_ratio,
        "entropy_gap": result.entropy_gap,
        "violations": result.violations,
        "trials": [
            {
                "temperature": t.temperature,
                "label": t.label,
                "unique_ratio": t.unique_ratio,
                "avg_latency_ms": t.avg_latency_ms,
                "hallucination": t.contains_hallucination,
                "run_count": len(t.outputs),
            }
            for t in result.trials
        ],
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"  📄 JSON report: {path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CORTEX Temperature Determinism Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--model",
        default="qwen2.5-coder:7b",
        help="Ollama model to benchmark (default: qwen2.5-coder:7b)",
    )
    p.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Runs per temperature point (default: 10)",
    )
    p.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: 5 runs (for fast CI feedback)",
    )
    p.add_argument(
        "--allow-skip",
        action="store_true",
        help="Exit 0 if Ollama is unreachable (use in CI without local Ollama)",
    )
    p.add_argument(
        "--json",
        metavar="PATH",
        help="Export results to JSON (useful for CI artifact upload)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-run output (only show final report)",
    )
    return p


async def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runs = 5 if args.quick else args.runs

    print("🌡️  CORTEX Temperature Determinism Benchmark")
    print(f"   Model  : {args.model}")
    print(f"   Runs   : {runs} per temperature")
    print(f"   Mode   : {'QUICK' if args.quick else 'FULL'}")

    try:
        result = await benchmark(
            model=args.model,
            runs=runs,
            verbose=not args.quiet,
        )
    except RuntimeError as exc:
        print(f"\n⚠️  {exc}")
        if args.allow_skip:
            print("   --allow-skip active: exiting 0 (skip gracefully)")
            return 0
        return 2

    print_report(result)

    if args.json:
        export_json(result, args.json)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
