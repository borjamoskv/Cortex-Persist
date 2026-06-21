# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class SealPrinter:
    """Unified printer for SEALS quality gates with timing and stub support."""

    def __init__(self) -> None:
        self.console = Console()

    def head(self, title: str) -> None:
        self.console.print()
        self.console.print(Panel(Text(title, style="bold blue"), border_style="blue"))

    def seal(self, gate_num: int, axiom: str, desc: str) -> None:
        self.console.print()
        self.console.print(f"[bold white]🔍 Gate {gate_num}:[/] {desc} ([dim]{axiom}[/])")
        self.console.print("─" * 40, style="dim")

    def success(self, msg: str) -> None:
        self.console.print(f"   [bold green]🟢 PASS[/] {msg}")

    def fail(self, msg: str) -> None:
        self.console.print(f"   [bold red]🔴 FAIL[/] {msg}")

    def warn(self, msg: str) -> None:
        self.console.print(f"   [bold yellow]🟡 WARN[/] {msg}")

    def info(self, msg: str) -> None:
        self.console.print(f"   [blue]ℹ[/] {msg}")

    def print(self, msg: str, style: str | None = None) -> None:
        """Generic print method for arbitrary output."""
        self.console.print(msg, style=style)

    def stub(self, msg: str) -> None:
        self.console.print(f"   [bold grey]⬜ STUB[/] {msg}")

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
            self.console.print(f"   [dim]⏱  Gate {gate_num}: {elapsed:.0f}ms[/]")
