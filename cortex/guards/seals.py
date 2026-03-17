#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""CORTEX Quality Gates (11 Seals) — Sovereign Local Enforcement.

Executes all 11 Axiom gates locally. Used by pre-push hooks and GitHub Actions.
Zero latency axiom enforcement (AX-020).

Seal 11: Cobbler's Compliance — the Red Team Swarm audits itself.
"""

from __future__ import annotations
from typing import Optional

import asyncio
import os
import sys
from pathlib import Path

from cortex.guards.sovereign_seals import (
    check_gate_15_dependency,
    check_gate_16_byzantine,
    check_gate_17_shannon,
    check_gate_18_evolution,
    check_gate_19_eu_ai,
    check_gate_20_noir,
    check_gate_21_preservation,
)


class SealPrinter:
    def head(self, title: str) -> None:
        print(f"\n{'━' * 60}")
        print(f" {title}")
        print(f"{'━' * 60}")

    def seal(self, gate_num: int, axiom: str, desc: str) -> None:
        print(f"\n{'─' * 40}")
        print(f"🔍 Gate {gate_num}: {desc} ({axiom})")

    def success(self, msg: str) -> None:
        print(f"   [🟢 PASSED] {msg}")

    def fail(self, msg: str) -> None:
        print(f"   [🔴 FAILED] {msg}")

    def warn(self, msg: str) -> None:
        print(f"   [🟡 WARN] {msg}")


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

        async def _read_file(p: Path) -> tuple[Path, Optional[str]]:
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


async def check_gate_1_lint() -> bool:
    printer.seal(1, "AX-011 Entropy Death", "Lint (Ruff)")
    code, out = await arun_cmd(["ruff", "check", "cortex/", "--output-format", "concise"])
    if code == 0:
        printer.success("Ruff checks passed.")
        return True
    elif code == 127:
        printer.warn("Ruff not found — skipping (install with: pip install ruff)")
        return True  # Non-blocking: tool absence != code violation
    else:
        printer.fail("Ruff linting failed.")
        print(out[:2000])  # Cap output to avoid flooding
        return False


async def check_gate_2_type() -> bool:
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
            return True
    if code == 0 or "Success: no issues found" in out or '"errorCount":0' in out:
        printer.success("Type checks passed.")
        return True
    else:
        printer.fail("Type checking failed.")
        print(out[:2000])
        return False


async def check_gate_3_security() -> bool:
    printer.seal(3, "AX-010 Zero Trust", "Security Scan (Bandit)")
    code, out = await arun_cmd(
        ["bandit", "-r", "cortex/", "-q", "--severity-level", "high", "--confidence-level", "high"]
    )
    if code == 0:
        printer.success("Bandit security scan passed.")
        return True
    elif code == 127:
        printer.warn("Bandit not found — skipping (install with: pip install bandit)")
        return True
    else:
        printer.fail("Security vulnerabilities detected.")
        print(out[:2000])
        return False


async def check_gate_4_tests() -> bool:
    printer.seal(4, "AX-017 Ledger Integrity", "Tests & Coverage")
    python_cmd = ROOT_DIR / ".venv" / "bin" / "python"
    if not python_cmd.exists():
        python_cmd = Path(sys.executable)
    # --timeout requires pytest-timeout; excluded for compatibility
    cmd = [str(python_cmd), "-m", "pytest", "tests/", "-x", "-q", "--tb=short", "-p", "no:timeout"]
    code, out = await arun_cmd(cmd)
    if code == 0:
        printer.success("All tests passed.")
        return True
    else:
        printer.fail("Tests failed.")
        print(out[:3000])
        return False


async def check_gate_5_ledger() -> bool:
    printer.seal(5, "AX-017 Ledger Integrity", "Schema Initialization")
    try:
        from cortex.engine import CortexEngine

        engine = CortexEngine(":memory:", auto_embed=False)
        await engine.init_db()
        await engine.close()
        printer.success("Ledger schema initialized successfully.")
        return True
    except Exception as e:  # noqa: BLE001 — test execution boundary
        printer.fail(f"Ledger initialization threw error: {e}")
        return False


async def check_gate_6_connection() -> bool:
    printer.seal(6, "AX-017 Ledger Integrity", "Connection Guard")
    python_cmd = ROOT_DIR / ".venv" / "bin" / "python"
    code, out = await arun_cmd(
        [str(python_cmd), "-m", "cortex.database.connection_guard", "--root", "cortex"]
    )
    if code == 0:
        printer.success("Connection guard passed.")
        return True
    else:
        printer.fail("Connection guard failed.")
        print(out)
        return False


async def check_gate_7_async() -> bool:
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
        return True
    else:
        printer.fail(f"Found blocking time.sleep(): {violations}")
        return False


async def check_gate_8_loc() -> bool:
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
        return True
    return False


async def check_gate_9_registry() -> bool:
    printer.seal(9, "Registry Integrity", "Axiom Registry Sync")
    try:
        from cortex.extensions.axioms import AXIOM_REGISTRY, AxiomCategory
        from cortex.extensions.axioms.registry import by_category, enforced
    except ImportError:
        printer.warn("Axioms extension not found. Skipping registry check.")
        return True

    try:
        total = len(AXIOM_REGISTRY)
        const = len(by_category(AxiomCategory.CONSTITUTIONAL))
        enf = len(enforced())

        if total < 20:
            printer.fail(f"Registry degraded: only {total} axioms (min 20)")
            return False
        if const < 3:
            printer.fail(f"Constitutional layer degraded: {const} items")
            return False

        printer.success(f"Registry load OK: {total} axioms, {enf} CI-enforced.")
        return True
    except Exception as e:  # noqa: BLE001 — registry loading boundary
        printer.fail(f"Registry error: {e}")
        return False


async def check_gate_10_prompt_size() -> bool:
    printer.seal(10, "Heuristic", "Prompt Size Check")
    prompt_file = ROOT_DIR / "SYSTEM_PROMPT.md"
    if not prompt_file.exists():
        printer.warn("No SYSTEM_PROMPT.md found.")
        return True

    try:
        content = await asyncio.to_thread(prompt_file.read_text, encoding="utf-8")
        tokens = len(content.split())
        if tokens > 500:
            printer.warn(f"System prompt is {tokens} words (target: <200).")
        else:
            printer.success(f"System prompt within targets ({tokens} words).")
    except OSError:
        printer.warn("Could not read SYSTEM_PROMPT.md")

    return True


async def check_gate_11_cobbler() -> bool:
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
        return False

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

    return passed


async def check_gate_12_determinism() -> bool:
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
        return False

    printer.success("Seal 12: Temperature Determinism Gate intact.")
    return True


async def check_gate_13_latency() -> bool:
    """Seal 13: A-Record Latency Drift.

    Fails if average local model latency exceeds 200ms in telemetry.
    """
    try:
        from cortex.extensions.llm._telemetry import CascadeTelemetry
    except ImportError:
        printer.warn("Seal 13 Skipped: LLM telemetry extension not found.")
        return True

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
        return True

    printer.success("Seal 13: A-Record Latency Gate intact (<200ms).")
    return True


async def check_gate_14_aesthetic() -> bool:
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
        return True

    printer.success("Seal 14: Sovereign Aesthetic Gate intact.")
    return True


async def main() -> int:
    printer.head("21 SEALS — CORTEX QUALITY GATES")

    # Pre-cache all Python files into memory concurrently. O(1) file traversals moving forward.
    await GlobalSourceCache.load()

    # SKIP_GATES: comma-separated gate numbers to skip (e.g. SKIP_GATES=4)
    # Useful when the test suite is too slow for SSH keepalive during git push.
    # Tests always run in CI — this only affects the local pre-push hook.
    _skip = {
        int(g.strip()) for g in os.environ.get("SKIP_GATES", "").split(",") if g.strip().isdigit()
    }

    async def _gate4() -> bool:
        if 4 in _skip:
            printer.seal(4, "SKIPPED", "Tests — skipped via SKIP_GATES")
            printer.warn("Gate 4 skipped (SKIP_GATES env). Run 'pytest tests/' separately.")
            return True
        return await check_gate_4_tests()

    results = await asyncio.gather(
        check_gate_1_lint(),
        check_gate_2_type(),
        check_gate_3_security(),
        _gate4(),
        check_gate_5_ledger(),
        check_gate_6_connection(),
        check_gate_7_async(),
        check_gate_8_loc(),
        check_gate_9_registry(),
        check_gate_11_cobbler(),  # Seal 11: Cobbler's Compliance
        check_gate_12_determinism(),
        check_gate_13_latency(),
        check_gate_14_aesthetic(),
        check_gate_15_dependency(),
        check_gate_16_byzantine(),
        check_gate_17_shannon(),
        check_gate_18_evolution(),
        check_gate_19_eu_ai(),
        check_gate_20_noir(),
        check_gate_21_preservation(),
    )
    # Check gate 10 independently (it never fails the run)
    await check_gate_10_prompt_size()

    printer.head("SEALS SUMMARY")
    failed = [i + 1 for i, r in enumerate(results) if not r]
    # Remap index 10 → seal 11 in the summary
    remapped = [11 if s == 10 else s for s in failed]

    if remapped:
        printer.fail(f"SEALS BROKEN: {remapped}")
        print("\nFix violations before pushing.")
        return 1
    else:
        printer.success("ALL 21 SEALS INTACT. Ready for launch.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
