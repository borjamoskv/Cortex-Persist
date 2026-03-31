"""Shared printer utilities for the seal checks."""

from __future__ import annotations


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
