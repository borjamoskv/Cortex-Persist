# cortex/evolution/telemetry.py
"""Lightweight telemetry log — appends one CSV line per cycle.

Allows graphing fitness progression across thousands of cycles
without parsing heavy JSON state files.

Output: ~/.cortex/evolution_telemetry.csv
"""

from __future__ import annotations

import csv
import logging
import time
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.evolution.engine import CycleReport

logger = logging.getLogger(__name__)

DEFAULT_TELEMETRY_PATH = Path("~/.cortex/evolution_telemetry.csv").expanduser()

_HEADER = [
    "timestamp",
    "cycle",
    "avg_agent_fit",
    "best_agent_fit",
    "worst_agent_fit",
    "avg_sub_fit",
    "mutations",
    "tournaments",
    "species",
    "duration_ms",
]


def _ensure_header(path: Path) -> None:
    """Write CSV header if file doesn't exist or is empty."""
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_HEADER)


def append_cycle(report: CycleReport, path: Path = DEFAULT_TELEMETRY_PATH) -> None:
    """Append a single cycle's metrics as one CSV row."""
    _ensure_header(path)
    row = [
        f"{time.time():.3f}",
        report.cycle,
        f"{report.avg_agent_fitness:.2f}",
        f"{report.best_agent_fitness:.2f}",
        f"{report.worst_agent_fitness:.2f}",
        f"{report.avg_subagent_fitness:.2f}",
        report.total_mutations,
        report.tournaments_run,
        report.species_count,
        f"{report.duration_ms:.2f}",
    ]
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def read_telemetry(
    path: Path = DEFAULT_TELEMETRY_PATH,
    last_n: int = 0,
) -> list[dict[str, str]]:
    """Read telemetry CSV. If last_n > 0, return only the last N rows."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if last_n > 0:
        return rows[-last_n:]
    return rows


def summary_text(path: Path = DEFAULT_TELEMETRY_PATH, last_n: int = 20) -> str:
    """Pretty-print the last N cycles as a compact table."""
    rows = read_telemetry(path, last_n)
    if not rows:
        return "No telemetry data available."

    out = StringIO()
    out.write(
        f"{'Cycle':>6} {'AvgFit':>7} {'Best':>6} {'Worst':>6} {'Muts':>5} {'Tourn':>5} {'ms':>6}\n"
    )
    out.write("─" * 48 + "\n")
    for r in rows:
        out.write(
            f"{r.get('cycle', '?'):>6} "
            f"{r.get('avg_agent_fit', '?'):>7} "
            f"{r.get('best_agent_fit', '?'):>6} "
            f"{r.get('worst_agent_fit', '?'):>6} "
            f"{r.get('mutations', '?'):>5} "
            f"{r.get('tournaments', '?'):>5} "
            f"{r.get('duration_ms', '?'):>6}\n"
        )
    return out.getvalue()
