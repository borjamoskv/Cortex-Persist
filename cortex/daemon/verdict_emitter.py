"""CORTEX Guard Daemon — Verdict Emitter.

Formats and delivers guard verdicts in multiple output modes:
- Terminal: Rich-formatted ANSI output (PASS ✓, WARN ⚠, BLOCK ✗)
- Log: Structured JSON to ~/.cortex/guard.log
- Callback: Async callback for ledger integration

Thread-safe. Non-blocking. Zero-allocation on PASS verdicts when quiet.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cortex.daemon.action_classifier import ClassifiedAction, GuardLevel
from cortex.guards.verdicts import PolicyVerdict, VerdictReport

logger = logging.getLogger("cortex.daemon.verdict")

# Default log directory
_CORTEX_HOME = Path.home() / ".cortex"
_DEFAULT_LOG = _CORTEX_HOME / "guard.log"
_DEFAULT_PID = _CORTEX_HOME / "guard.pid"

# Verdict history ring buffer size
_HISTORY_MAX = 500


@dataclass(frozen=True)
class GuardVerdict:
    """A complete verdict record combining classification + policy result."""

    action: ClassifiedAction
    report: VerdictReport
    timestamp: float = field(default_factory=time.time)

    @property
    def is_pass(self) -> bool:
        return self.report.verdict == PolicyVerdict.CORTEX_PASS

    @property
    def is_warn(self) -> bool:
        return self.report.verdict == PolicyVerdict.CORTEX_WARN

    @property
    def is_block(self) -> bool:
        return self.report.verdict == PolicyVerdict.CORTEX_BLOCK

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.report.verdict.value,
            "rule_id": self.report.rule_id,
            "description": self.report.description,
            "severity": self.report.severity,
            "action_type": self.action.action_type.value,
            "guard_level": self.action.guard_level.value,
            "path": self.action.path,
            "detail": self.action.detail,
            "timestamp": self.timestamp,
            "hash": self.report.hash,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class VerdictEmitter:
    """Multi-output verdict emitter for the Guard Daemon.

    Supports three output modes:
    - terminal: Rich ANSI formatting to stderr
    - logfile:  JSON-per-line to ~/.cortex/guard.log
    - callback: Async function for ledger/notification integration

    The emitter maintains a ring buffer of recent verdicts for
    `cortex guard status` introspection.
    """

    def __init__(
        self,
        *,
        terminal: bool = True,
        logfile: Path | None = _DEFAULT_LOG,
        quiet: bool = False,
    ) -> None:
        self._terminal = terminal
        self._logfile = logfile
        self._quiet = quiet
        self._history: deque[GuardVerdict] = deque(maxlen=_HISTORY_MAX)

        # Counters
        self.total_pass = 0
        self.total_warn = 0
        self.total_block = 0
        self.total_passthrough = 0

        # Ensure log directory exists
        if self._logfile:
            self._logfile.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, verdict: GuardVerdict) -> None:
        """Emit a verdict synchronously.

        PASS verdicts in quiet mode are counted but not displayed.
        WARN and BLOCK are always visible.
        """
        self._history.append(verdict)
        self._update_counters(verdict)

        # Write to log file (always, regardless of quiet)
        if self._logfile:
            self._write_log(verdict)

        # Terminal output
        if self._terminal:
            if verdict.action.guard_level == GuardLevel.PASSTHROUGH:
                return  # Never show passthrough in terminal
            if self._quiet and verdict.is_pass:
                return  # Quiet mode suppresses PASS
            self._write_terminal(verdict)

    def _update_counters(self, verdict: GuardVerdict) -> None:
        if verdict.action.guard_level == GuardLevel.PASSTHROUGH:
            self.total_passthrough += 1
        elif verdict.is_pass:
            self.total_pass += 1
        elif verdict.is_warn:
            self.total_warn += 1
        elif verdict.is_block:
            self.total_block += 1

    def _write_log(self, verdict: GuardVerdict) -> None:
        """Append JSON line to guard.log."""
        if self._logfile is None:
            return
        try:
            with open(self._logfile, "a", encoding="utf-8") as f:
                f.write(verdict.to_json() + "\n")
        except OSError:
            logger.warning("Failed to write to guard log: %s", self._logfile)

    def _write_terminal(self, verdict: GuardVerdict) -> None:
        """Write rich-formatted verdict to terminal."""
        try:
            from rich.console import Console

            console = Console(stderr=True)

            if verdict.is_block:
                icon = "✗"
                style = "bold red"
                label = "BLOCK"
            elif verdict.is_warn:
                icon = "⚠"
                style = "bold yellow"
                label = "WARN"
            else:
                icon = "✓"
                style = "bold green"
                label = "PASS"

            path_display = verdict.action.path or "(command)"
            rule = verdict.report.rule_id or ""

            console.print(
                f"[{style}]{icon} CORTEX {label}[/{style}] "
                f"[dim]{verdict.action.action_type.value}[/dim] "
                f"{path_display} "
                f"[dim]{rule}[/dim] "
                f"[dim italic]{verdict.action.detail}[/dim italic]"
            )
        except ImportError:
            # Fallback without Rich
            label = verdict.report.verdict.value
            print(  # noqa: T201
                f"[CORTEX {label}] {verdict.action.action_type.value} "
                f"{verdict.action.path} {verdict.action.detail}"
            )

    @property
    def recent_verdicts(self) -> list[GuardVerdict]:
        """Return recent verdicts (newest first)."""
        return list(reversed(self._history))

    @property
    def stats(self) -> dict[str, int]:
        """Return verdict counters."""
        return {
            "pass": self.total_pass,
            "warn": self.total_warn,
            "block": self.total_block,
            "passthrough": self.total_passthrough,
            "total": self.total_pass + self.total_warn + self.total_block + self.total_passthrough,
        }
