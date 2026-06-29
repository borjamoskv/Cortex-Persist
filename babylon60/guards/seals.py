#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
# SPDX-License-Identifier: Apache-2.0
"""CORTEX Quality Gates (10 Sovereign Seals) - Local Enforcement.

Consolidated from 21 Seals → 10 orthogonal verification axes.
Eliminated 4 stubs (16, 18, 19, 20) and merged related checks.
Zero latency axiom enforcement (AX-V).

Usage:
    python -m cortex.guards.seals
    FAIL_FAST=1 python -m cortex.guards.seals
    SKIP_GATES=3,6 python -m cortex.guards.seals
    ONLY_GATES=1,2 python -m cortex.guards.seals
    FORCE_GATES=4 python -m cortex.guards.seals
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

from babylon60.guards._seals_cache import GlobalSourceCache, printer
from babylon60.guards._seals_checks_1_5 import (
    check_seal_1_code_quality,
    check_seal_2_type_safety,
    check_seal_3_security,
    check_seal_4_tests,
    check_seal_5_ledger,
)
from babylon60.guards._seals_checks_6_10 import (
    check_seal_6_async_perf,
    check_seal_7_axiom_registry,
    check_seal_8_dependency,
    check_seal_9_compliance,
    check_seal_10_preservation,
)

# ── Gate Result Type ──
GateResult = tuple[bool, str]

# ── Gate Registry ──
_GATE_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def _parse_gate_filters() -> tuple[set[int], set[int], set[int]]:
    """Extract gate filters from environment variables."""

    def _to_set(var: str) -> set[int]:
        return {int(g.strip()) for g in os.environ.get(var, "").split(",") if g.strip().isdigit()}

    skip = _to_set("SKIP_GATES")
    only = _to_set("ONLY_GATES")
    force = _to_set("FORCE_GATES")

    if only:
        skip = {gn for gn in _GATE_ORDER if gn not in only}

    return skip, only, force


async def _execute_gates_loop(
    gate_order: list[int],
    gate_fns: dict[int, Callable[[], Coroutine[Any, Any, GateResult]]],
    skip: set[int],
    force: set[int],
    fail_fast: bool,
) -> dict[int, GateResult]:
    """Run the defined gates and return results mapping."""
    results: dict[int, GateResult] = {}

    for gate_num in gate_order:
        if gate_num in skip:
            printer.seal(gate_num, "SKIPPED", f"Seal {gate_num} - skipped via Filtering")
            results[gate_num] = (True, "skipped")
            continue

        if gate_num in force:
            printer.warn(f"Seal {gate_num} - FORCE VALIDATION (Bypassing auto-skip)")

        start = time.perf_counter()
        res = await gate_fns[gate_num]()
        elapsed = (time.perf_counter() - start) * 1000
        printer.print(f"   [dim]⏱  {elapsed:.0f}ms[/]")

        results[gate_num] = res
        if fail_fast and not res[0]:
            printer.fail(f"FAIL-FAST: Seal {gate_num} failed. Aborting.")
            break

    return results


def _print_summary(results: dict[int, GateResult], total_elapsed: float) -> int:
    """Print the final seals summary and return exit code."""
    printer.head("SOVEREIGN SEALS SUMMARY")

    verified = [gn for gn, (p, k) in results.items() if k == "verified" and p]
    skipped = [gn for gn, (_, k) in results.items() if k == "skipped"]
    failed = [gn for gn, (p, k) in results.items() if not p]

    printer.print(
        f"   [bold green]🟢 VERIFIED: {len(verified)}[/]  "
        f"[bold yellow]🟡 SKIPPED: {len(skipped)}[/]  "
        f"[bold red]🔴 FAILED: {len(failed)}[/]"
    )
    printer.print(f"   [dim]⏱  Total: {total_elapsed:.0f}ms[/]")

    if failed:
        printer.fail(f"SEALS BROKEN: {sorted(failed)}\nFix violations before pushing.")
        return 1
    printer.success(f"ALL {len(verified)} SOVEREIGN SEALS INTACT. Ready for launch.")
    return 0


async def main() -> int:
    total_start = time.perf_counter()
    printer.head("10 SOVEREIGN SEALS - CORTEX QUALITY GATES")

    await GlobalSourceCache.load()

    skip, only, force = _parse_gate_filters()
    # Gate 4 (tests) requires full dev deps - only enable with explicit opt-in
    full_seals = os.environ.get("CORTEX_FULL_SEALS", "").strip() in ("1", "true", "yes")

    # Auto-skip Gate 4 unless CORTEX_FULL_SEALS is explicitly set
    if not full_seals and 4 not in force and 4 not in only:
        if 4 not in skip:
            printer.warn("Ω₂ EXERGY PRESERVATION: Running in FAST MODE (Gate 4 SKIPPED).")
            skip.add(4)

    fail_fast = os.environ.get("FAIL_FAST", "").strip() in ("1", "true", "yes")

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

    results = await _execute_gates_loop(_GATE_ORDER, gate_fns, skip, force, fail_fast)
    total_elapsed = (time.perf_counter() - total_start) * 1000

    return _print_summary(results, total_elapsed)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
