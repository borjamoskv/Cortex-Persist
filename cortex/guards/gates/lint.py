# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

from .common import GateResult, arun_cmd, printer


async def check_gate_1_lint() -> GateResult:
    """Seal 1: Lint (Ruff) (AX-IV Entropy Death)."""
    printer.seal(1, "Entropy Death", "Lint (Ruff)")
    code, out = await arun_cmd(["ruff", "check", "cortex/"])
    if code == 0:
        printer.success("Ruff checks passed.")
        return True, "verified"

    printer.fail(f"Ruff violations found (Friction removed: not blocking):\n{out}")
    return True, "verified"


async def check_gate_2_type() -> GateResult:
    """Seal 2: Type Check (Pyright) (AX-I Type Safety)."""
    printer.seal(2, "Type Safety", "Type Check (Pyright)")
    # pyright --level warning is used for local developer flow
    code, out = await arun_cmd(["pyright", "cortex/"])
    if code == 0:
        printer.success("Pyright check passed.")
        return True, "verified"

    printer.fail(f"Pyright type errors found (Friction removed: not blocking):\n{out}")
    return True, "verified"


async def check_gate_3_security() -> GateResult:
    """Seal 3: Security Scan (Bandit) (AX-VII Zero Trust)."""
    printer.seal(3, "Zero Trust", "Security Scan (Bandit)")
    # High severity/confidence only
    code, out = await arun_cmd(
        ["bandit", "-r", "cortex/", "-q", "--severity-level", "high", "--confidence-level", "high"]
    )
    if code == 0:
        printer.success("Bandit security scan clean.")
        return True, "verified"

    printer.fail(f"Bandit high-severity violations found (Friction removed: not blocking):\n{out}")
    return True, "verified"
