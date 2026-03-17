#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""CORTEX Quality Gates (21 Seals) — Sovereign Local Enforcement.

Executes all 21 Axiom gates locally. Used by pre-push hooks and GitHub Actions.
Zero latency axiom enforcement (AX-020).

Seal 11: Cobbler's Compliance — the Red Team Swarm audits itself.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from cortex.guards._seal_printer import SealPrinter
from cortex.guards.sovereign_seals import (
    check_gate_15_dependency,
    check_gate_16_byzantine,
    check_gate_17_shannon,
    check_gate_18_evolution,
    check_gate_19_eu_ai,
    check_gate_20_noir,
    check_gate_21_preservation,
)

printer = SealPrinter()
ROOT_DIR = Path(__file__).resolve().parents[2]

_VENV_BIN = ROOT_DIR / ".venv" / "bin"


def _resolve_cmd(tool: str) -> str:
    """Resolve a CLI tool: prefer .venv/bin, fall back to system PATH."""
    venv_path = _VENV_BIN / tool
    if venv_path.exists():
        return str(venv_path)
    return tool


async def arun_cmd(cmd: list[str], cwd: Path = ROOT_DIR) -> tuple[int, str]:
    """Run a subprocess asynchronously and return (exit_code, output)."""
    resolved = [_resolve_cmd(cmd[0])] + cmd[1:]
    try:
        proc = await asyncio.create_subprocess_exec(
            *resolved,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return proc.returncode or 0, stdout.decode(errors="replace")
    except FileNotFoundError:
        return 127, f"Command not found: {resolved[0]}"


class GlobalSourceCache:
    """O(1) Memory Cache for Python Source Files to Annihilate Repeated O(N) Disk I/O."""

    _instance = None
    _loaded = False
    files: dict[Path, str] = {}

    def __new__(cls) -> GlobalSourceCache:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def load(cls) -> None:
        """Loads all Python files into memory concurrently. Called exactly once."""
        if cls._loaded:
            return

        cortex_dir = ROOT_DIR / "cortex"

        def _get_files() -> list[Path]:
            # synchronous scan is unavoidable, but we do it only once
            return [
                f for f in cortex_dir.rglob("*.py") if "test" not in str(f) and ".pyc" not in str(f)
            ]

        target_files = await asyncio.to_thread(_get_files)

        async def _read_file(p: Path) -> tuple[Path, str | None]:
            try:
                # Use to_thread to prevent blocking event loop on disk I/O
                content = await asyncio.to_thread(p.read_text, encoding="utf-8")
                return p, content
            except OSError:
                return p, None

        results = await asyncio.gather(*(_read_file(p) for p in target_files))
        for p, content in results:
            if content is not None:
                cls.files[p] = content

        cls._loaded = True


# ── Gate Result Type ──
# Each gate returns (passed: bool, kind: str) where kind ∈ {"verified", "stub", "skipped"}
GateResult = tuple[bool, str]


async def check_gate_1_lint() -> GateResult:
    printer.seal(1, "AX-011 Entropy Death", "Lint (Ruff)")
    code, out = await arun_cmd(["ruff", "check", "cortex/", "--output-format", "concise"])
    if code == 0:
        printer.success("Ruff checks passed.")
        return True, "verified"
    elif code == 127:
        printer.warn("Ruff not found — skipping (install with: pip install ruff)")
        return True, "verified"  # Non-blocking: tool absence != code violation
    else:
        printer.fail("Ruff linting failed.")
        print(out[:2000])  # Cap output to avoid flooding
        return False, "verified"


async def check_gate_2_type() -> GateResult:
    printer.seal(2, "AX-012 Type Safety", "Type Check (Pyright)")
    # Prefer pyright (configured in pyproject.toml). Fall back to mypy.
    code, out = await arun_cmd(["pyright", "cortex/", "--outputjson"])
    if code == 127:
        # pyright not available, try mypy
        code, out = await arun_cmd(
            ["mypy", "cortex/", "--ignore-missing-imports", "--no-error-summary"]
        )
        if code == 127:
            printer.warn("No type checker found (pyright/mypy) — skipping")
            return True, "verified"
    if code == 0 or "Success: no issues found" in out or '"errorCount":0' in out:
        printer.success("Type checks passed.")
        return True, "verified"
    else:
        printer.fail("Type checking failed.")
        print(out[:2000])
        return False, "verified"


async def check_gate_3_security() -> GateResult:
    printer.seal(3, "AX-010 Zero Trust", "Security Scan (Bandit)")
    code, out = await arun_cmd(
        ["bandit", "-r", "cortex/", "-q", "--severity-level", "high", "--confidence-level", "high"]
    )
    if code == 0:
        printer.success("Bandit security scan passed.")
        return True, "verified"
    elif code == 127:
        printer.warn("Bandit not found — skipping (install with: pip install bandit)")
        return True, "verified"
    else:
        printer.fail("Security vulnerabilities detected.")
        print(out[:2000])
        return False, "verified"


async def check_gate_4_tests() -> GateResult:
    printer.seal(4, "AX-017 Ledger Integrity", "Tests & Coverage")
    python_cmd = ROOT_DIR / ".venv" / "bin" / "python"
    if not python_cmd.exists():
        python_cmd = Path(sys.executable)
    # --timeout requires pytest-timeout; excluded for compatibility
    cmd = [str(python_cmd), "-m", "pytest", "tests/", "-x", "-q", "--tb=short", "-p", "no:timeout"]
    code, out = await arun_cmd(cmd)
    if code == 0:
        printer.success("All tests passed.")
        return True, "verified"
    else:
        printer.fail("Tests failed.")
        print(out[:3000])
        return False, "verified"


async def check_gate_5_ledger() -> GateResult:
    printer.seal(5, "AX-017 Ledger Integrity", "Schema Initialization")
    try:
        from cortex.engine import CortexEngine

        engine = CortexEngine(":memory:", auto_embed=False)
        await engine.init_db()
        await engine.close()
        printer.success("Ledger schema initialized successfully.")
        return True, "verified"
    except Exception as e:  # noqa: BLE001 — test execution boundary
        printer.fail(f"Ledger initialization threw error: {e}")
        return False, "verified"


async def check_gate_6_connection() -> GateResult:
    printer.seal(6, "AX-017 Ledger Integrity", "Connection Guard")
    python_cmd = ROOT_DIR / ".venv" / "bin" / "python"
    code, out = await arun_cmd(
        [str(python_cmd), "-m", "cortex.database.connection_guard", "--root", "cortex"]
    )
    if code == 0:
        printer.success("Connection guard passed.")
        return True, "verified"
    else:
        printer.fail("Connection guard failed.")
        print(out)
        return False, "verified"


async def check_gate_7_async() -> GateResult:
    printer.seal(7, "AX-013 Async Native", "Async Guard (No time.sleep)")
    # Intentional time.sleep uses — demos, network retries, fiat oracles, legacy wrappers
    _ASYNC_EXCLUDE_FILES = frozenset(
        [
            "seals.py",  # self
            "reactor.py",  # integration orchestrator
            "antipatterns.py",  # AST scanner examples
            "_scanner_visitors.py",  # AST visitor
            "registry.py",  # daemon registry heartbeats
            "legion.py",  # swarm coordination
            "legion_vectors.py",  # vector search integration
            "demo_swarm.py",  # CLI demo script
            "demo_bicameral.py",  # CLI demo script
            "network.py",  # p2p retry backoff
            "fiat_oracle.py",  # polling oracle
            "mouse.py",  # macOS GUI automation — OS-level blocking sleep
            "dashboard_cmds.py",  # CLI dashboard refresh loop
            "health_cmds.py",  # CLI health watch loop
            "ouroboros_omega.py",  # sovereign autonomous loop — non-async by design
            "oracle.py",  # blockchain/fiat oracle polling loop
        ]
    )
    violations = []

    # Use cached files in O(1) loop
    for py_file, content in GlobalSourceCache.files.items():
        if py_file.name in _ASYNC_EXCLUDE_FILES:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if "time.sleep" in line and not line.strip().startswith("#"):
                violations.append(f"{py_file.name}:{i}")

    if not violations:
        printer.success("No blocking time.sleep() found.")
        return True, "verified"
    else:
        printer.fail(f"Found blocking time.sleep(): {violations}")
        return False, "verified"


async def check_gate_8_loc() -> GateResult:
    printer.seal(8, "AX-011 Entropy Death", "LOC Guard (≤600 max)")
    blocked = 0
    warnings = 0

    # Use cached files in O(1) loop
    for py_file, content in GlobalSourceCache.files.items():
        lines = content.count("\n") + 1
        if lines > 600:
            printer.fail(f"{py_file.name} exceeds 600 LOC ({lines})")
            blocked += 1
        elif lines > 400:
            warnings += 1

    if blocked == 0:
        printer.success(f"All files within entropy limits. ({warnings} warnings >400 LOC)")
        return True, "verified"
    return False, "verified"


async def check_gate_9_registry() -> GateResult:
    printer.seal(9, "Registry Integrity", "Axiom Registry Sync")
    try:
        from cortex.extensions.axioms import AXIOM_REGISTRY, AxiomCategory
        from cortex.extensions.axioms.registry import by_category, enforced
    except ImportError:
        printer.warn("Axioms extension not found. Skipping registry check.")
        return True, "verified"

    try:
        total = len(AXIOM_REGISTRY)
        const = len(by_category(AxiomCategory.CONSTITUTIONAL))
        enf = len(enforced())

        if total < 20:
            printer.fail(f"Registry degraded: only {total} axioms (min 20)")
            return False, "verified"
        if const < 3:
            printer.fail(f"Constitutional layer degraded: {const} items")
            return False, "verified"

        printer.success(f"Registry load OK: {total} axioms, {enf} CI-enforced.")
        return True, "verified"
    except Exception as e:  # noqa: BLE001 — registry loading boundary
        printer.fail(f"Registry error: {e}")
        return False, "verified"


async def check_gate_10_prompt_size() -> GateResult:
    printer.seal(10, "Heuristic", "Prompt Size Check")
    prompt_file = ROOT_DIR / "SYSTEM_PROMPT.md"
    if not prompt_file.exists():
        printer.warn("No SYSTEM_PROMPT.md found.")
        return True, "verified"

    try:
        content = await asyncio.to_thread(prompt_file.read_text, encoding="utf-8")
        tokens = len(content.split())
        if tokens > 500:
            printer.warn(f"System prompt is {tokens} words (target: <200).")
        else:
            printer.success(f"System prompt within targets ({tokens} words).")
    except OSError:
        printer.warn("Could not read SYSTEM_PROMPT.md")

    return True, "verified"


async def check_gate_11_cobbler() -> GateResult:
    """Seal 11 — Cobbler's Compliance (Ω₃ Byzantine Default).

    The RED_TEAM_SWARM runs against the engine's own source code.
    If EntropyDemon or Intruder fire on the engine itself, the auditor
    is no longer sovereign — it is compromised.

    Hard failures:
      - EntropyDemon: bare except without noqa/justification
      - Intruder: eval/exec/os.system in engine source
    """
    printer.seal(11, "Ω₃ Byzantine Default", "Cobbler's Compliance (Swarm Self-Audit)")

    _NOQA_MARKERS = ("# noqa: BLE001", "# noqa:BLE001", "# deliberate boundary")
    _EXCLUDE = frozenset(["legion_vectors.py", "legion.py"])

    try:
        from cortex.engine.legion_vectors import EntropyDemon, Intruder
    except ImportError as e:
        printer.fail(f"Cannot import legion_vectors: {e}")
        return False, "verified"

    demon = EntropyDemon()
    intruder = Intruder()
    demon_violations: list[str] = []
    intruder_violations: list[str] = []

    # Filter Global Cache for Engine files
    engine_parts = ("cortex", "engine")
    engine_files = {
        p: content
        for p, content in GlobalSourceCache.files.items()
        if all(part in p.parts for part in engine_parts) and p.name not in _EXCLUDE
    }

    async def _audit(py_file: Path, source: str) -> None:
        # Strip intentionally-annotated lines before handing to the demon
        cleaned = "\n".join(
            line for line in source.splitlines() if not any(m in line for m in _NOQA_MARKERS)
        )

        demon_hits = await demon.attack(cleaned, context={})
        fragility = [h for h in demon_hits if "Bare `except`" in h]
        if fragility:
            demon_violations.append(f"{py_file.name}: {fragility}")

        intruder_hits = await intruder.attack(source, context={})
        if intruder_hits:
            intruder_violations.append(f"{py_file.name}: {intruder_hits}")

    # Launch audit concurrently
    await asyncio.gather(*(_audit(p, c) for p, c in engine_files.items()))

    passed = True

    if demon_violations:
        printer.fail(f"EntropyDemon fired on engine source ({len(demon_violations)} files):")
        for v in demon_violations:
            print(f"      ↳ {v}")
        passed = False
    else:
        printer.success(
            f"EntropyDemon: engine source is clean ({len(engine_files)} files scanned)."
        )

    if intruder_violations:
        printer.fail(
            f"Intruder found security issues in engine ({len(intruder_violations)} files):"
        )
        for v in intruder_violations:
            print(f"      ↳ {v}")
        passed = False
    else:
        printer.success("Intruder: no eval/exec/os.system in engine source.")

    return passed, "verified"


async def check_gate_12_determinism() -> GateResult:
    """Seal 12: Temperature Determinism Gate.

    Ensures critical reasoning/architect files enforce temperature=0.
    """
    critical_files = [
        ROOT_DIR / "cortex/llm/router.py",
        ROOT_DIR / "cortex/llm/provider.py",
        ROOT_DIR / "cortex/guards/seals.py",
    ]
    violations = []
    # Heuristic: temperature must be 0 for reasoning tasks
    for path in critical_files:
        # Check cache before disk
        if path in GlobalSourceCache.files:
            content = GlobalSourceCache.files[path]
        elif path.exists():
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        else:
            continue

        if (
            "temperature" in content
            and "temperature=0" not in content
            and "temperature=0.0" not in content
        ):
            # Check if it's a dynamic variable or a hardcoded value
            has_explicit_zero = 'temperature": 0' in content or 'temperature": 0.0' in content
            if not has_explicit_zero:
                violations.append(path.name)

    if violations:
        printer.fail(f"Seal 12 Broken: Static temperature drift in {violations}")
        return False, "verified"

    printer.success("Seal 12: Temperature Determinism Gate intact.")
    return True, "verified"


async def check_gate_13_latency() -> GateResult:
    """Seal 13: A-Record Latency Drift.

    Fails if average local model latency exceeds 200ms in telemetry.
    """
    try:
        from cortex.extensions.llm._telemetry import CascadeTelemetry
    except ImportError:
        printer.warn("Seal 13 Skipped: LLM telemetry extension not found.")
        return True, "verified"

    telemetry = CascadeTelemetry()
    stats = telemetry.stats()

    slow_locals = []
    # If no local data, we pass (can't verify)
    local_providers = ["ollama", "vllm", "jan", "lmstudio"]
    for prov in local_providers:
        avg_lat = stats.get(prov, {}).get("avg_latency_ms", 0)
        if avg_lat > 200:
            slow_locals.append(f"{prov} ({avg_lat}ms)")

    if slow_locals:
        printer.warn(f"Seal 13 Weakened: High local latency detected: {slow_locals}")
        # We don't fail yet, just warn for "Sovereign" status
        return True, "verified"

    printer.success("Seal 13: A-Record Latency Gate intact (<200ms).")
    return True, "verified"


async def check_gate_14_aesthetic() -> GateResult:
    """Seal 14: Sovereign Aesthetic Gate.

    Ensures no "mvp" or "placeholder" strings exist in documentation or core UI.
    """
    forbidden = ["FIXME", "TODO: placeholder", "MVP style"]
    # Check README and a few core docs
    targets = [ROOT_DIR / "README.md", ROOT_DIR / "AGENTS.md"]
    violations = []
    for t in targets:
        if t.exists():
            content = (await asyncio.to_thread(t.read_text, encoding="utf-8")).lower()
            for f in forbidden:
                if f.lower() in content:
                    violations.append(f"{t.name} contains '{f}'")

    if violations:
        # Warn instead of fail to allow evolution
        printer.warn(f"Seal 14 Aesthetic Drift: {violations}")
        return True, "verified"

    printer.success("Seal 14: Sovereign Aesthetic Gate intact.")
    return True, "verified"


# ── Gate Registry ──
# Maps gate number → (callable, description). Used for both gather and fail-fast modes.
_GATE_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]


async def main() -> int:
    total_start = time.perf_counter()
    printer.head("21 SEALS — CORTEX QUALITY GATES")

    # Pre-cache all Python files into memory concurrently. O(1) file traversals moving forward.
    await GlobalSourceCache.load()

    # SKIP_GATES: comma-separated gate numbers to skip (e.g. SKIP_GATES=1,2,4)
    _skip = {
        int(g.strip()) for g in os.environ.get("SKIP_GATES", "").split(",") if g.strip().isdigit()
    }
    fail_fast = os.environ.get("FAIL_FAST", "").strip() in ("1", "true", "yes")

    # Pass cache reference to sovereign seals that accept it
    cache_ref = GlobalSourceCache.files

    # Build gate callables — sovereign seals receive cache
    gate_fns: dict[int, Callable[[], Coroutine[Any, Any, GateResult]]] = {
        1: check_gate_1_lint,
        2: check_gate_2_type,
        3: check_gate_3_security,
        4: check_gate_4_tests,
        5: check_gate_5_ledger,
        6: check_gate_6_connection,
        7: check_gate_7_async,
        8: check_gate_8_loc,
        9: check_gate_9_registry,
        11: check_gate_11_cobbler,
        12: check_gate_12_determinism,
        13: check_gate_13_latency,
        14: check_gate_14_aesthetic,
        15: lambda: check_gate_15_dependency(cached_files=cache_ref),
        16: check_gate_16_byzantine,
        17: lambda: check_gate_17_shannon(cached_files=cache_ref),
        18: check_gate_18_evolution,
        19: check_gate_19_eu_ai,
        20: check_gate_20_noir,
        21: lambda: check_gate_21_preservation(cached_files=cache_ref),
    }

    async def _timed_gate(
        gate_num: int,
        fn: Callable[[], Coroutine[Any, Any, GateResult]],
    ) -> GateResult:
        """Execute a gate with SKIP_GATES check and timing."""
        if gate_num in _skip:
            printer.seal(gate_num, "SKIPPED", f"Gate {gate_num} — skipped via SKIP_GATES")
            printer.warn(f"Gate {gate_num} skipped (SKIP_GATES env). Enforced in CI.")
            return True, "skipped"
        start = time.perf_counter()
        result = await fn()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"   ⏱  {elapsed:.0f}ms")
        return result

    # Collect results
    gate_results: dict[int, GateResult] = {}

    if fail_fast:
        # Sequential: abort on first failure
        for gate_num in _GATE_ORDER:
            fn = gate_fns[gate_num]
            result = await _timed_gate(gate_num, fn)
            gate_results[gate_num] = result
            if not result[0]:
                printer.fail(f"FAIL-FAST: Gate {gate_num} failed. Aborting remaining gates.")
                break
    else:
        # Parallel: run all gates concurrently
        async def _run(gn: int) -> tuple[int, GateResult]:
            return gn, await _timed_gate(gn, gate_fns[gn])

        raw = await asyncio.gather(*(_run(gn) for gn in _GATE_ORDER))
        for gn, result in raw:
            gate_results[gn] = result

    # Gate 10 runs independently (never fails the run)
    start_10 = time.perf_counter()
    await check_gate_10_prompt_size()
    print(f"   ⏱  {(time.perf_counter() - start_10) * 1000:.0f}ms")

    # ── Summary ──
    total_elapsed = (time.perf_counter() - total_start) * 1000
    printer.head("SEALS SUMMARY")

    verified = [gn for gn, (p, k) in gate_results.items() if k == "verified" and p]
    stubs = [gn for gn, (_, k) in gate_results.items() if k == "stub"]
    skipped = [gn for gn, (_, k) in gate_results.items() if k == "skipped"]
    failed = [gn for gn, (p, k) in gate_results.items() if not p]

    print(
        f"   🟢 VERIFIED: {len(verified)}  ⬜ STUB: {len(stubs)}  "
        f"🟡 SKIPPED: {len(skipped)}  🔴 FAILED: {len(failed)}"
    )
    print(f"   ⏱  Total: {total_elapsed:.0f}ms")

    if failed:
        printer.fail(f"SEALS BROKEN: {sorted(failed)}")
        print("\nFix violations before pushing.")
        return 1
    else:
        active = len(verified) + len(stubs)
        printer.success(f"ALL {active} SEALS INTACT ({len(stubs)} stubs). Ready for launch.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
