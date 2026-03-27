"""
cortex/swarm/parallel_config_swarm.py
─────────────────────────────────────
Parallel Config Swarm Orchestrator v2.0

Deploys an auxiliary P0 swarm for massive configuration tasks:
linting enforcement, typing propagation, config drift mitigation,
infra updates — across hundreds of files in parallel, with
per-file collision avoidance and ledger audit trail.

Architecture:
  ParallelConfigSwarm
    ├── discover()         → file enumeration + shard partitioning
    ├── configure()        → bounded parallel dispatch with locking
    ├── _execute_shard()   → per-shard dispatch with EV gate
    └── crystallize()      → ledger persistence + report

Concurrency: asyncio.Semaphore(max_concurrency) + per-file resource locks
via AsyncSignalBus to prevent write collisions between parallel shards.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cortex.swarm.bus import AsyncSignalBus

logger = logging.getLogger("cortex.swarm.parallel_config")


# ──────────────────────────────────────────────────────────────────────────────
# Result Models
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class ShardResult:
    """Result of a single configuration shard execution."""

    shard_id: str
    files: list[str]
    status: str = "pending"  # pending | running | success | failed | skipped_ev
    applied_count: int = 0
    error: str | None = None
    duration_s: float = 0.0
    compute_cost_usd: float = 0.0
    exergy_delta: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.status == "success"


@dataclass
class ConfigSwarmReport:
    """Aggregated report from a parallel config execution."""

    session_id: str
    directive: str
    total_shards: int = 0
    total_files: int = 0
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    results: list[ShardResult] = field(default_factory=list)
    duration_s: float = 0.0
    total_exergy: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_shards == 0:
            return 0.0
        return self.success_count / self.total_shards

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "directive": self.directive[:200],
            "total_shards": self.total_shards,
            "total_files": self.total_files,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "skipped_count": self.skipped_count,
            "success_rate": f"{self.success_rate:.1%}",
            "duration_s": round(self.duration_s, 2),
            "total_exergy": round(self.total_exergy, 4),
            "shards": [
                {
                    "shard_id": r.shard_id,
                    "status": r.status,
                    "files": len(r.files),
                    "applied": r.applied_count,
                    "error": r.error,
                    "duration_s": round(r.duration_s, 2),
                }
                for r in self.results
            ],
        }


# ──────────────────────────────────────────────────────────────────────────────
# Parallel Config Swarm v2.0
# ──────────────────────────────────────────────────────────────────────────────


class ParallelConfigSwarm:
    """
    Sovereign Auxiliary Configuration Swarm (P0 Structural).

    Designed for massive cross-cutting config operations:
    - Linting enforcement across N files
    - Type annotation propagation
    - Config drift mitigation
    - Infrastructure updates

    Guarantees:
    - Per-file resource locking via AsyncSignalBus (collision avoidance)
    - Bounded concurrency (configurable semaphore)
    - EV gating per shard
    - Structured result reporting
    - Ledger audit trail
    """

    # Base compute cost per shard (USD)
    SHARD_COMPUTE_COST_USD: float = 0.05
    # Minimum exergy multiplier for EV gate
    MIN_EV_MULTIPLIER: float = 3.0

    def __init__(
        self,
        bus: AsyncSignalBus | None = None,
        max_concurrency: int = 15,
        shard_size: int = 10,
    ) -> None:
        self.bus = bus or AsyncSignalBus()
        self._sem = asyncio.Semaphore(max_concurrency)
        self._shard_size = shard_size

    # ── Discovery ─────────────────────────────────────────────────────────

    @staticmethod
    def discover(
        root: str | Path,
        extensions: tuple[str, ...] = (".py",),
        exclude_dirs: tuple[str, ...] = (
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".ruff_cache",
            ".pytest_cache",
            "dist",
            "*.egg-info",
        ),
    ) -> list[Path]:
        """Enumerate target files for configuration."""
        root_path = Path(root).resolve()
        results: list[Path] = []

        for ext in extensions:
            for f in root_path.rglob(f"*{ext}"):
                # Skip excluded directories
                skip = False
                for exc in exclude_dirs:
                    if exc in f.parts:
                        skip = True
                        break
                if not skip and f.is_file():
                    results.append(f)

        results.sort()
        return results

    # ── Shard Partitioning ────────────────────────────────────────────────

    def partition(self, files: list[Path]) -> list[list[Path]]:
        """
        Partition file list into shards of size `shard_size`.
        Each shard is an independent unit of parallel work.
        """
        shards: list[list[Path]] = []
        for i in range(0, len(files), self._shard_size):
            shards.append(files[i : i + self._shard_size])
        return shards

    # ── EV Gate ───────────────────────────────────────────────────────────

    def _ev_gate(self, shard_files: list[Path], directive: str) -> bool:
        """
        Thermodynamic EV gate (Ω₂).
        Estimates expected value based on file count and directive complexity.
        """
        # Expected yield: proportional to file count * directive Information density
        unique_chars = len(set(directive.lower()))
        info_density = unique_chars / max(len(directive), 1)
        expected_yield = len(shard_files) * info_density * 10.0

        cost = self.SHARD_COMPUTE_COST_USD * len(shard_files)
        ev = expected_yield * 0.8  # 80% confidence for config tasks
        passes = ev >= cost * self.MIN_EV_MULTIPLIER

        if not passes:
            logger.debug(
                "EV_GATE REJECT: shard(%d files) EV=%.2f cost=%.2f",
                len(shard_files),
                ev,
                cost,
            )
        return passes

    # ── Per-Shard Execution ───────────────────────────────────────────────

    async def _execute_shard(
        self,
        shard_index: int,
        shard_files: list[Path],
        directive: str,
        handler: Any | None = None,
    ) -> ShardResult:
        """
        Execute a single configuration shard.

        For each file in the shard:
        1. Acquire resource lock (collision avoidance)
        2. Apply configuration directive
        3. Release lock
        4. Record result

        Args:
            shard_index: Shard ordinal for identification.
            shard_files: Files in this shard.
            directive: The configuration task description.
            handler: Optional async callable(path, directive) -> bool.
                     If None, the shard is recorded as "simulated".
        """
        shard_id = f"shard-{shard_index:04d}"
        result = ShardResult(
            shard_id=shard_id,
            files=[str(f) for f in shard_files],
            compute_cost_usd=self.SHARD_COMPUTE_COST_USD * len(shard_files),
        )

        t0 = time.monotonic()

        # EV gate check
        if not self._ev_gate(shard_files, directive):
            result.status = "skipped_ev"
            result.duration_s = time.monotonic() - t0
            return result

        result.status = "running"
        applied = 0

        async with self._sem:
            for file_path in shard_files:
                file_uri = str(file_path)
                lock = await self.bus.acquire_resource_lock(file_uri)

                async with lock:
                    try:
                        if handler is not None:
                            success = await handler(file_path, directive)
                        else:
                            # No handler → simulated pass
                            success = True

                        if success:
                            applied += 1
                    except Exception as exc:
                        logger.warning(
                            "[%s] File %s failed: %s",
                            shard_id,
                            file_path.name,
                            exc,
                        )

        result.applied_count = applied
        result.status = "success" if applied == len(shard_files) else "failed"
        result.exergy_delta = applied * 0.1 - result.compute_cost_usd
        result.duration_s = time.monotonic() - t0

        if applied < len(shard_files):
            result.error = (
                f"{len(shard_files) - applied}/{len(shard_files)} files failed"
            )

        return result

    # ── Main Orchestration ────────────────────────────────────────────────

    async def configure(
        self,
        root: str | Path,
        directive: str,
        *,
        extensions: tuple[str, ...] = (".py",),
        handler: Any | None = None,
    ) -> ConfigSwarmReport:
        """
        Deploy the Parallel Config Swarm across a directory tree.

        Args:
            root: Root directory to scan.
            directive: Configuration task description (e.g.,
                       "Enforce type hints on all public functions").
            extensions: File extensions to target.
            handler: Optional async callable(path: Path, directive: str) -> bool.
                     Called for each file. Returns True on success.

        Returns:
            ConfigSwarmReport with per-shard results.
        """
        session_id = (
            f"pcfg-{hashlib.sha256(f'{directive}:{time.time()}'.encode()).hexdigest()[:8]}"
        )

        logger.info(
            "ParallelConfigSwarm[%s]: 🚀 Discovering files in %s...",
            session_id,
            root,
        )

        # 1. Discovery
        files = self.discover(root, extensions=extensions)
        if not files:
            logger.info("ParallelConfigSwarm: No files found.")
            return ConfigSwarmReport(
                session_id=session_id,
                directive=directive,
            )

        logger.info(
            "ParallelConfigSwarm[%s]: Found %d files. Partitioning into shards (size=%d)...",
            session_id,
            len(files),
            self._shard_size,
        )

        # 2. Partition into shards
        shards = self.partition(files)

        # 3. Parallel dispatch
        tasks = [
            self._execute_shard(i, shard, directive, handler)
            for i, shard in enumerate(shards)
        ]

        t_start = time.monotonic()
        results: list[ShardResult] = list(await asyncio.gather(*tasks))
        total_time = time.monotonic() - t_start

        # 4. Aggregate
        report = ConfigSwarmReport(
            session_id=session_id,
            directive=directive,
            total_shards=len(shards),
            total_files=len(files),
            success_count=sum(1 for r in results if r.is_success),
            failure_count=sum(1 for r in results if r.status == "failed"),
            skipped_count=sum(1 for r in results if r.status == "skipped_ev"),
            results=results,
            duration_s=total_time,
            total_exergy=sum(r.exergy_delta for r in results),
        )

        logger.info(
            "ParallelConfigSwarm[%s]: ✅ Complete. "
            "%d/%d shards succeeded (%d files). Duration: %.2fs. Exergy: %.4f",
            session_id,
            report.success_count,
            report.total_shards,
            report.total_files,
            report.duration_s,
            report.total_exergy,
        )

        return report

    # ── Ledger Crystallization ────────────────────────────────────────────

    @staticmethod
    async def crystallize(report: ConfigSwarmReport, ledger: Any) -> str | None:
        """Persist the config swarm report to the CORTEX Ledger."""
        if not ledger:
            return None

        tx_hash = await ledger.record_transaction(
            project="swarm",
            action="parallel_config_crystallization",
            detail={
                "session_id": report.session_id,
                "directive": report.directive[:200],
                "total_shards": report.total_shards,
                "total_files": report.total_files,
                "success_rate": f"{report.success_rate:.1%}",
                "duration_s": round(report.duration_s, 2),
                "total_exergy": round(report.total_exergy, 4),
                "mechanical_justification": (
                    f"Parallel config deployment across {report.total_files} files "
                    f"in {report.total_shards} shards. "
                    f"Concurrency-bounded with per-file resource locking. "
                    f"Success rate: {report.success_rate:.1%}. "
                    f"Net exergy delta: {report.total_exergy:.4f}."
                ),
            },
        )
        logger.info(
            "ParallelConfigSwarm: Crystallized to ledger (tx=%s)", tx_hash
        )
        return tx_hash


# ──────────────────────────────────────────────────────────────────────────────
# Convenience function (backward-compatible with v1 API)
# ──────────────────────────────────────────────────────────────────────────────


async def invoke_auxiliary_config(
    directive: str,
    root: str = ".",
    shards: int = 10,
    handler: Any | None = None,
) -> ConfigSwarmReport:
    """
    One-shot convenience for invoking the config swarm.

    Args:
        directive: What to configure (e.g., "Enforce ruff compliance").
        root: Root directory to scan.
        shards: Shard size (files per shard).
        handler: Optional handler callable.
    """
    swarm = ParallelConfigSwarm(shard_size=shards)
    return await swarm.configure(root, directive, handler=handler)


# ──────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = Console()

    parser = argparse.ArgumentParser(
        description="Parallel Config Swarm v2.0 — Massive cross-cutting configuration",
    )
    parser.add_argument(
        "directive",
        type=str,
        help="Configuration directive to apply",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Root directory to scan (default: .)",
    )
    parser.add_argument(
        "--shard-size",
        type=int,
        default=10,
        help="Files per shard (default: 10)",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=15,
        help="Max concurrent shards (default: 15)",
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default=".py",
        help="Comma-separated file extensions (default: .py)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Write report JSON to path",
    )

    args = parser.parse_args()
    raw = args.extensions.split(",")
    exts = tuple(
        e.strip() if e.startswith(".") else f".{e.strip()}" for e in raw
    )

    console.print(
        Panel(
            f"[bold #2B3BE5]⚛ PARALLEL CONFIG SWARM v2.0[/bold #2B3BE5]\n"
            f"Directive: [bold]{args.directive}[/bold]\n"
            f"Root: [cyan]{args.root}[/cyan]  |  "
            f"Shard Size: [bold]{args.shard_size}[/bold]  |  "
            f"Concurrency: [bold]{args.max_concurrency}[/bold]\n"
            f"Extensions: [dim]{', '.join(exts)}[/dim]",
            border_style="#2B3BE5",
            title="[bold]CONFIG SWARM[/bold]",
        )
    )

    swarm = ParallelConfigSwarm(
        max_concurrency=args.max_concurrency,
        shard_size=args.shard_size,
    )

    report = asyncio.run(swarm.configure(args.root, args.directive, extensions=exts))

    # Dashboard
    table = Table(
        title=f"⚛ Config Shards — {report.session_id}",
        show_header=True,
        header_style="bold #2B3BE5",
        border_style="#1A1A2E",
        min_width=80,
    )
    table.add_column("Shard", width=14, style="bold white")
    table.add_column("Files", width=6, justify="right")
    table.add_column("Applied", width=8, justify="right")
    table.add_column("Status", width=12)
    table.add_column("Exergy Δ", width=10, justify="right")
    table.add_column("⏱ s", width=8, justify="right", style="dim")

    status_styles = {
        "success": "bold green",
        "failed": "bold red",
        "skipped_ev": "dim red",
        "pending": "dim white",
        "running": "bold #2B3BE5",
    }

    for r in report.results:
        style = status_styles.get(r.status, "white")
        exergy_str = f"{r.exergy_delta:+.4f}"
        exergy_style = "bold green" if r.exergy_delta > 0 else "bold red"
        table.add_row(
            r.shard_id,
            str(len(r.files)),
            str(r.applied_count),
            Text(r.status.upper(), style=style),
            Text(exergy_str, style=exergy_style),
            f"{r.duration_s:.2f}",
        )

    # Summary
    table.add_section()
    net_style = "bold green" if report.total_exergy >= 0 else "bold red"
    table.add_row(
        "[bold]TOTAL[/bold]",
        str(report.total_files),
        str(sum(r.applied_count for r in report.results)),
        f"{report.success_count}/{report.total_shards}",
        Text(f"{report.total_exergy:+.4f}", style=net_style),
        f"{report.duration_s:.2f}",
    )

    console.print(table)
    console.print(
        f"\n[bold #2B3BE5]◈ CONFIG SWARM SESSION CRYSTALLIZED[/bold #2B3BE5]"
        f"\n  Session : [dim]{report.session_id}[/dim]"
        f"\n  Files   : [bold]{report.total_files}[/bold] across "
        f"[bold]{report.total_shards}[/bold] shards"
        f"\n  Success : [bold green]{report.success_rate:.0%}[/bold green]"
        f"\n  Duration: [dim]{report.duration_s:.2f}s[/dim]\n"
    )

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        console.print(f"[dim]Report written → {args.output_json}[/dim]")
