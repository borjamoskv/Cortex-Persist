# This file is part of CORTEX. Apache-2.0.
"""Shared SealPrinter — extracted to break circular import between seals ↔ sovereign_seals."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager


class SealPrinter:
    """Unified printer for SEALS quality gates with timing and stub support."""

    def head(self, title: str) -> None:
        print(f"\n{'━' * 60}")
        print(f" {title}")
        print(f"{'━' * 60}")

    def seal(self, gate_num: int, axiom: str, desc: str) -> None:
        print(f"\n{'─' * 40}")
        print(f"🔍 Gate {gate_num}: {desc} ({axiom})")

    def success(self, msg: str) -> None:
        print(f"   [🟢 PASS] {msg}")

    def fail(self, msg: str) -> None:
        print(f"   [🔴 FAIL] {msg}")

    def warn(self, msg: str) -> None:
        print(f"   [🟡 WARN] {msg}")

    def stub(self, msg: str) -> None:
        print(f"   [⬜ STUB] {msg}")

    @contextmanager
    def timed(self, gate_num: int) -> Generator[dict[str, float], None, None]:
        """Context manager that measures and prints gate execution time.

        Usage:
            with printer.timed(1) as t:
                result = await check_gate_1_lint()
            # t["elapsed_ms"] now has the elapsed time
        """
        result: dict[str, float] = {"elapsed_ms": 0.0}
        start = time.perf_counter()
        try:
            yield result
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            result["elapsed_ms"] = elapsed
            print(f"   ⏱  Gate {gate_num}: {elapsed:.0f}ms")
