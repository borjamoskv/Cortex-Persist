#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""CORTEX Quality Gates (10 Seals) — Sovereign Local Enforcement.

Executes all 10 Axiom gates locally. Used by pre-push hooks and GitHub Actions.
Zero latency axiom enforcement (AX-020).
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path


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


def run_cmd(cmd: list[str], cwd: Path = ROOT_DIR) -> tuple[int, str]:
    """Run a subprocess and return (exit_code, output)."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout + proc.stderr
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"


async def check_gate_1_lint() -> bool:
    printer.seal(1, "AX-011 Entropy Death", "Lint (Ruff)")
    code, out = run_cmd(["ruff", "check", "cortex/"])
    if code == 0:
        printer.success("Ruff checks passed.")
        return True
    else:
        printer.fail("Ruff linting failed.")
        print(out)
        return False


async def check_gate_2_type() -> bool:
    printer.seal(2, "AX-012 Type Safety", "Type Check (Mypy)")
    code, out = run_cmd(["mypy", "cortex/", "--ignore-missing-imports", "--no-error-summary"])
    if code == 0 or "Success: no issues found" in out:
        printer.success("Mypy strict checks passed.")
        return True
    else:
        printer.fail("Mypy type checking failed.")
        print(out)
        return False


async def check_gate_3_security() -> bool:
    printer.seal(3, "AX-010 Zero Trust", "Security Scan (Bandit)")
    code, out = run_cmd(
        ["bandit", "-r", "cortex/", "-q", "-c", "pyproject.toml", "--severity-level", "high"]
    )
    if code == 0:
        printer.success("Bandit security scan passed.")
        return True
    else:
        printer.fail("Security vulnerabilities detected.")
        print(out)
        return False


async def check_gate_4_tests() -> bool:
    printer.seal(4, "AX-017 Ledger Integrity", "Tests & Coverage")
    # Quick fast-fail test mode local
    code, out = run_cmd(["python", "-m", "pytest", "tests/", "-x", "-q", "--timeout=10"])
    if code == 0:
        printer.success("All tests passed.")
        return True
    else:
        printer.fail("Tests failed.")
        print(out)
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
    except Exception as e:
        printer.fail(f"Ledger initialization threw error: {e}")
        return False


async def check_gate_6_connection() -> bool:
    printer.seal(6, "AX-017 Ledger Integrity", "Connection Guard")
    code, out = run_cmd(["python", "-m", "cortex.database.connection_guard", "--root", "cortex"])
    if code == 0:
        printer.success("Connection guard passed.")
        return True
    else:
        printer.fail("Connection guard failed.")
        print(out)
        return False


async def check_gate_7_async() -> bool:
    printer.seal(7, "AX-013 Async Native", "Async Guard (No time.sleep)")
    violations = []
    for py_file in ROOT_DIR.joinpath("cortex").rglob("*.py"):
        if "test" in str(py_file) or ".pyc" in str(py_file):
            continue
        with open(py_file, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if "time.sleep" in line and not line.strip().startswith("#"):
                    violations.append(f"{py_file.name}:{i}")

    if not violations:
        printer.success("No blocking time.sleep() found.")
        return True
    else:
        printer.fail(f"Found blocking time.sleep(): {violations}")
        return False


async def check_gate_8_loc() -> bool:
    printer.seal(8, "AX-011 Entropy Death", "LOC Guard (≤500 max)")
    blocked = 0
    warnings = 0
    for py_file in ROOT_DIR.joinpath("cortex").rglob("*.py"):
        if "test" in str(py_file) or ".pyc" in str(py_file):
            continue
        try:
            with open(py_file, encoding="utf-8") as f:
                lines = sum(1 for _ in f)
                if lines > 500:
                    printer.fail(f"{py_file.name} exceeds 500 LOC ({lines})")
                    blocked += 1
                elif lines > 300:
                    warnings += 1
        except Exception:
            pass

    if blocked == 0:
        printer.success(f"All files within entropy limits. ({warnings} warnings >300 LOC)")
        return True
    return False


async def check_gate_9_registry() -> bool:
    printer.seal(9, "Registry Integrity", "Axiom Registry Sync")
    try:
        from cortex.axioms import AXIOM_REGISTRY, AxiomCategory
        from cortex.axioms.registry import by_category, enforced

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
    except Exception as e:
        printer.fail(f"Registry error: {e}")
        return False


async def check_gate_10_prompt_size() -> bool:
    printer.seal(10, "Heuristic", "Prompt Size Check")
    prompt_file = ROOT_DIR / "SYSTEM_PROMPT.md"
    if not prompt_file.exists():
        printer.warn("No SYSTEM_PROMPT.md found.")
        return True

    tokens = len(prompt_file.read_text("utf-8").split())
    if tokens > 500:
        printer.warn(f"System prompt is {tokens} words (target: <200).")
    else:
        printer.success(f"System prompt within targets ({tokens} words).")
    return True


async def main() -> int:
    printer.head("10 SEALS — CORTEX QUALITY GATES")

    results = await asyncio.gather(
        check_gate_1_lint(),
        check_gate_2_type(),
        check_gate_3_security(),
        check_gate_4_tests(),
        check_gate_5_ledger(),
        check_gate_6_connection(),
        check_gate_7_async(),
        check_gate_8_loc(),
        check_gate_9_registry(),
    )
    # Check gate 10 independently (it never fails the run)
    await check_gate_10_prompt_size()

    printer.head("SEALS SUMMARY")
    failed = [i + 1 for i, r in enumerate(results) if not r]

    if failed:
        printer.fail(f"SEALS BROKEN: {failed}")
        print("\nFix violations before pushing.")
        return 1
    else:
        printer.success("ALL 10 SEALS INTACT. Ready for launch.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
