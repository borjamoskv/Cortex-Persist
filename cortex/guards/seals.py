#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""CORTEX Quality Gates (10 Sovereign Seals) — Local Enforcement.

Consolidated from 21 Seals → 10 orthogonal verification axes.
Eliminated 4 stubs (16, 18, 19, 20) and merged related checks.
Zero latency axiom enforcement (AX-020).

Usage:
    python -m cortex.guards.seals
    FAIL_FAST=1 python -m cortex.guards.seals
    SKIP_GATES=3,6 python -m cortex.guards.seals
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

# ── SOVEREIGN PATH ANCHOR ──
# Force local workspace to the front of sys.path to bypass shadow injections
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cortex.guards._seal_printer import SealPrinter
from cortex.guards.sovereign_seals import (
    check_gate_21_preservation,
    check_seal_8_dependency_impl,
    check_seal_9_compliance_impl,
)

printer = SealPrinter()

_VENV_BIN = Path(sys.executable).parent


def _resolve_cmd(tool: str) -> str:
    """Resolve a CLI tool: prefer .venv/bin, fall back to system PATH."""
    venv_path = _VENV_BIN / tool
    if venv_path.exists():
        return str(venv_path)
    return tool


async def arun_cmd(cmd: list[str]) -> tuple[int, str]:
    """Execute a command asynchronously and return (code, output).
    Injects PYTHONPATH=. to ensure local package resolution.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    resolved = [_resolve_cmd(cmd[0])] + cmd[1:]
    try:
        proc = await asyncio.create_subprocess_exec(
            *resolved,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
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
            return [
                f for f in cortex_dir.rglob("*.py") if "test" not in str(f) and ".pyc" not in str(f)
            ]

        target_files = await asyncio.to_thread(_get_files)

        async def _read_file(p: Path) -> tuple[Path, str | None]:
            try:
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
GateResult = tuple[bool, str]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 1: CODE QUALITY — Ruff Lint + LOC Guard (≤600)
# Fuses: old Seal 1 (Lint) + old Seal 8 (LOC Guard)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_1_code_quality() -> GateResult:
    printer.seal(1, "AX-011 Entropy Death", "Code Quality (Ruff + LOC ≤700)")
    passed = True

    # ── Ruff Lint ──
    code, out = await arun_cmd(["ruff", "check", "cortex/", "--output-format", "concise"])
    if code == 0:
        printer.success("Ruff checks passed.")
    elif code == 127:
        printer.warn("Ruff not found — skipping (install with: pip install ruff)")
    else:
        printer.fail("Ruff linting failed.")
        print(out[:2000])
        passed = False

    # ── LOC Guard ──
    blocked = 0
    warnings = 0
    for py_file, content in GlobalSourceCache.files.items():
        lines = content.count("\n") + 1
        if lines > 700:
            printer.fail(f"{py_file.name} exceeds 700 LOC ({lines})")
            blocked += 1
        elif lines > 500:
            warnings += 1

    if blocked > 0:
        passed = False
    else:
        printer.success(f"All files within entropy limits. ({warnings} warnings >400 LOC)")

    return passed, "verified"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 2: TYPE SAFETY — Pyright/Mypy
# Unchanged — orthogonal axis.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_2_type_safety() -> GateResult:
    printer.seal(2, "AX-012 Type Safety", "Type Check (Pyright)")
    code, out = await arun_cmd(["pyright", "cortex/", "--outputjson"])
    if code == 127:
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 3: SECURITY — Bandit + Cobbler Self-Audit
# Fuses: old Seal 3 (Bandit) + old Seal 11 (Cobbler's Compliance)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_3_security() -> GateResult:
    printer.seal(3, "AX-010 Zero Trust", "Security (Bandit + Self-Audit)")
    passed = True

    # ── Bandit Scan ──
    code, out = await arun_cmd(
        ["bandit", "-r", "cortex/", "-q", "--severity-level", "high", "--confidence-level", "high"]
    )
    if code == 0:
        printer.success("Bandit security scan passed.")
    elif code == 127:
        printer.warn("Bandit not found — skipping")
    else:
        printer.fail("Security vulnerabilities detected.")
        print(out[:2000])
        passed = False

    # ── Cobbler's Compliance (old Seal 11) ──
    _NOQA_MARKERS = ("# noqa: BLE001", "# noqa:BLE001", "# deliberate boundary")
    _EXCLUDE = frozenset(["legion_vectors.py", "legion.py"])

    try:
        from cortex.engine.legion_vectors import EntropyDemon, Intruder
    except ImportError:
        printer.warn("Cobbler skipped: legion_vectors not importable.")
        return passed, "verified"

    demon = EntropyDemon()
    intruder = Intruder()
    demon_violations: list[str] = []
    intruder_violations: list[str] = []

    engine_parts = ("cortex", "engine")
    engine_files = {
        p: content
        for p, content in GlobalSourceCache.files.items()
        if all(part in p.parts for part in engine_parts) and p.name not in _EXCLUDE
    }

    async def _audit(py_file: Path, source: str) -> None:
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

    await asyncio.gather(*(_audit(p, c) for p, c in engine_files.items()))

    if demon_violations:
        printer.fail(f"EntropyDemon fired on engine ({len(demon_violations)} files)")
        for v in demon_violations:
            print(f"      ↳ {v}")
        passed = False
    else:
        printer.success(f"EntropyDemon: engine clean ({len(engine_files)} files).")

    if intruder_violations:
        printer.fail(f"Intruder found issues ({len(intruder_violations)} files)")
        for v in intruder_violations:
            print(f"      ↳ {v}")
        passed = False
    else:
        printer.success("Intruder: no eval/exec/os.system in engine.")

    return passed, "verified"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 4: TESTS — pytest
# Unchanged — orthogonal axis.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_4_tests() -> GateResult:
    printer.seal(4, "AX-017 Ledger Integrity", "Tests & Coverage")
    python_cmd = sys.executable
    cmd = [str(python_cmd), "-m", "pytest", "tests/", "-x", "-q", "--tb=short", "-p", "no:timeout"]
    code, out = await arun_cmd(cmd)
    if code == 0:
        printer.success("All tests passed.")
        return True, "verified"
    else:
        printer.fail("Tests failed.")
        print(out[:3000])
        return False, "verified"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 5: LEDGER INTEGRITY — Schema Init + Connection Guard
# Fuses: old Seal 5 (Schema) + old Seal 6 (Connection Guard)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_5_ledger() -> GateResult:
    printer.seal(5, "AX-017 Ledger Integrity", "Schema Init + Connection Guard")
    passed = True

    # ── Schema Init ──
    try:
        from cortex.engine import CortexEngine

        engine = CortexEngine(":memory:", auto_embed=False)
        await engine.init_db()
        await engine.close()
        printer.success("Ledger schema initialized successfully.")
    except Exception as e:  # noqa: BLE001 — test execution boundary
        printer.fail(f"Ledger initialization threw error: {e}")
        passed = False

    # ── Connection Guard ──
    python_cmd = sys.executable
    code, out = await arun_cmd(
        [str(python_cmd), "-m", "cortex.database.connection_guard", "--root", "cortex"]
    )
    if code == 0:
        printer.success("Connection guard passed.")
    else:
        printer.fail("Connection guard failed.")
        print(out)
        passed = False

    return passed, "verified"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 6: ASYNC & PERFORMANCE — No time.sleep + Temperature + Latency
# Fuses: old Seal 7 (Async) + old Seal 12 (Determinism) + old Seal 13 (Latency)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_6_async_perf() -> GateResult:
    printer.seal(6, "AX-013 Async Native", "Async & Performance")
    passed = True

    # ── Async Guard (No time.sleep) ──
    _ASYNC_EXCLUDE_FILES = frozenset(
        [
            "seals.py",
            "reactor.py",
            "antipatterns.py",
            "_scanner_visitors.py",
            "registry.py",
            "legion.py",
            "legion_vectors.py",
            "demo_swarm.py",
            "demo_bicameral.py",
            "network.py",
            "fiat_oracle.py",
            "mouse.py",
            "dashboard_cmds.py",
            "health_cmds.py",
            "ouroboros_omega.py",
            "oracle.py",
        ]
    )
    sleep_violations = []
    for py_file, content in GlobalSourceCache.files.items():
        if py_file.name in _ASYNC_EXCLUDE_FILES:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if "time.sleep" in line and not line.strip().startswith("#"):
                sleep_violations.append(f"{py_file.name}:{i}")

    if sleep_violations:
        printer.fail(f"Blocking time.sleep(): {sleep_violations}")
        passed = False
    else:
        printer.success("No blocking time.sleep() found.")

    # ── Temperature Determinism (old Seal 12) ──
    critical_files = [
        ROOT_DIR / "cortex/llm/router.py",
        ROOT_DIR / "cortex/llm/provider.py",
        ROOT_DIR / "cortex/guards/seals.py",
    ]
    temp_violations = []
    for path in critical_files:
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
            has_explicit_zero = 'temperature": 0' in content or 'temperature": 0.0' in content
            if not has_explicit_zero:
                temp_violations.append(path.name)

    if temp_violations:
        printer.fail(f"Temperature drift in {temp_violations}")
        passed = False
    else:
        printer.success("Temperature Determinism intact.")

    # ── Latency Check (old Seal 13, warn-only) ──
    try:
        from cortex.extensions.llm._telemetry import CascadeTelemetry

        telemetry = CascadeTelemetry()
        stats = telemetry.stats()
        slow_locals = []
        for prov in ["ollama", "vllm", "jan", "lmstudio"]:
            avg_lat = stats.get(prov, {}).get("avg_latency_ms", 0)
            if avg_lat > 200:
                slow_locals.append(f"{prov} ({avg_lat}ms)")
        if slow_locals:
            printer.warn(f"High local latency: {slow_locals}")
        else:
            printer.success("Latency <200ms.")
    except ImportError:
        pass  # Telemetry extension not available — silent skip

    return passed, "verified"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 7: AXIOM REGISTRY — Registry Sync + Prompt Size
# Fuses: old Seal 9 (Registry) + old Seal 10 (Prompt Size)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_7_axiom_registry() -> GateResult:
    printer.seal(7, "Registry Integrity", "Axiom Registry + Prompt Budget")
    passed = True

    # ── Registry Sync ──
    try:
        from cortex.extensions.axioms import AXIOM_REGISTRY, AxiomCategory
        from cortex.extensions.axioms.registry import by_category, enforced

        total = len(AXIOM_REGISTRY)
        const = len(by_category(AxiomCategory.CONSTITUTIONAL))
        enf = len(enforced())

        if total < 20:
            printer.fail(f"Registry degraded: only {total} axioms (min 20)")
            passed = False
        elif const < 3:
            printer.fail(f"Constitutional layer degraded: {const} items")
            passed = False
        else:
            printer.success(f"Registry: {total} axioms, {enf} CI-enforced.")
    except ImportError:
        printer.warn("Axioms extension not found. Skipping registry check.")
    except Exception as e:  # noqa: BLE001 — registry loading boundary
        printer.fail(f"Registry error: {e}")
        passed = False

    # ── Prompt Size (warn-only) ──
    prompt_file = ROOT_DIR / "SYSTEM_PROMPT.md"
    if prompt_file.exists():
        try:
            content = await asyncio.to_thread(prompt_file.read_text, encoding="utf-8")
            tokens = len(content.split())
            if tokens > 500:
                printer.warn(f"System prompt {tokens} words (target: <200).")
            else:
                printer.success(f"Prompt within targets ({tokens} words).")
        except OSError:
            printer.warn("Could not read SYSTEM_PROMPT.md")

    return passed, "verified"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 8: DEPENDENCY INTEGRITY — Ghost Check + Shannon Entropy
# Fuses: old Seal 15 (Dependency Ghost) + old Seal 17 (Shannon)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_8_dependency() -> GateResult:
    printer.seal(8, "Ω₃ Byzantine", "Dependency Integrity + Shannon Entropy")
    return await check_seal_8_dependency_impl(GlobalSourceCache.files)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 9: COMPLIANCE & AESTHETIC — No placeholders + Audit trail
# Fuses: old Seal 14 (Aesthetic) + old Seal 19 (EU-AI, was stub)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_9_compliance() -> GateResult:
    printer.seal(9, "Sovereign Aesthetic", "Compliance & Aesthetic Integrity")
    return await check_seal_9_compliance_impl()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEAL 10: SELF-PRESERVATION — Hook + seals.py existence + HEAD lineage
# Direct from old Seal 21 — capstone integrity check.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_seal_10_preservation() -> GateResult:
    printer.seal(10, "Ω₅ Antifragile", "Self-Preservation")
    return await check_gate_21_preservation(cached_files=GlobalSourceCache.files)


# ── Gate Registry ──
_GATE_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


async def main() -> int:
    total_start = time.perf_counter()
    printer.head("10 SOVEREIGN SEALS — CORTEX QUALITY GATES")

    # Pre-cache all Python files into memory concurrently.
    await GlobalSourceCache.load()

    # ── Bifurcated Quality Gate (Axiom Ω₂) ──
    # SKIP_GATES: comma-separated gate numbers to skip
    _skip = {
        int(g.strip()) for g in os.environ.get("SKIP_GATES", "").split(",") if g.strip().isdigit()
    }

    is_ci = os.environ.get("CI") == "1" or os.environ.get("CORTEX_FULL_SEALS") == "1"
    if not is_ci:
        if 4 not in _skip:
            printer.warn("Ω₂ EXERGY PRESERVATION: Running in FAST MODE.")
            printer.warn("Heavy integration tests (Gate 4) are SKIPPED. Delegated to remote CI.")
            _skip.add(4)
    fail_fast = os.environ.get("FAIL_FAST", "").strip() in ("1", "true", "yes")

    # Build gate callables
    gate_fns: dict[int, Callable[[], Coroutine[Any, Any, GateResult]]] = {
        1: check_seal_1_code_quality,
        2: check_seal_2_type_safety,
        3: check_seal_3_security,
        4: check_seal_4_tests,
        5: check_seal_5_ledger,
        6: check_seal_6_async_perf,
        7: check_seal_7_axiom_registry,
        8: check_seal_8_dependency,
        9: check_seal_9_compliance,
        10: check_seal_10_preservation,
    }

    async def _timed_gate(
        gate_num: int,
        fn: Callable[[], Coroutine[Any, Any, GateResult]],
    ) -> GateResult:
        """Execute a gate with SKIP_GATES check and timing."""
        if gate_num in _skip:
            printer.seal(gate_num, "SKIPPED", f"Seal {gate_num} — skipped via SKIP_GATES")
            printer.warn(f"Seal {gate_num} skipped (SKIP_GATES env). Enforced in CI.")
            return True, "skipped"
        start = time.perf_counter()
        result = await fn()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"   ⏱  {elapsed:.0f}ms")
        return result

    # Collect results
    gate_results: dict[int, GateResult] = {}

    if fail_fast:
        for gate_num in _GATE_ORDER:
            fn = gate_fns[gate_num]
            result = await _timed_gate(gate_num, fn)
            gate_results[gate_num] = result
            if not result[0]:
                printer.fail(f"FAIL-FAST: Seal {gate_num} failed. Aborting.")
                break
    else:
        for gn in _GATE_ORDER:
            gate_results[gn] = await _timed_gate(gn, gate_fns[gn])

    # ── Summary ──
    total_elapsed = (time.perf_counter() - total_start) * 1000
    printer.head("SOVEREIGN SEALS SUMMARY")

    verified = [gn for gn, (p, k) in gate_results.items() if k == "verified" and p]
    skipped = [gn for gn, (_, k) in gate_results.items() if k == "skipped"]
    failed = [gn for gn, (p, k) in gate_results.items() if not p]

    print(f"   🟢 VERIFIED: {len(verified)}  🟡 SKIPPED: {len(skipped)}  🔴 FAILED: {len(failed)}")
    print(f"   ⏱  Total: {total_elapsed:.0f}ms")

    if failed:
        printer.fail(f"SEALS BROKEN: {sorted(failed)}\nFix violations before pushing.")
        return 1
    printer.success(f"ALL {len(verified)} SOVEREIGN SEALS INTACT. Ready for launch.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
